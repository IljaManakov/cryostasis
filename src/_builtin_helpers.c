#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <object.h>

#include <stdbool.h>


// __class__ assignment in Python is normally only allowed for non-builtins or modules.
// Since we also want to freeze builtin containers, we have to work around that limitation.
// Similarly, assigning __class__ on types with __slots__ is already possible in pure Python but only
// if the types have a common base and have the same slots, which is not true in our case.
static PyObject*
_set_class_on_builtin_or_slots(PyObject* module, PyObject* args)
{
    PyObject* object;
    PyObject* new_class;
    if (!PyArg_ParseTuple(args, "OO", &object, &new_class)) {
        PyErr_SetString(PyExc_TypeError,
                        "_set_class_on_builtin_or_slots must be called with two arguments: object and new_class");
        return NULL;
    }

    if (new_class == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete __class__ attribute");
        return NULL;
    }
    if (!PyType_Check(new_class)) {
        PyErr_Format(PyExc_TypeError,
          "__class__ must be set to a class, not '%s' object",
          Py_TYPE(new_class)->tp_name);
        return NULL;
    }

    PyTypeObject* obj_type = Py_TYPE(object);
    PyTypeObject* new_class_tp = (PyTypeObject*)new_class;

    bool is_builtin_container = PyType_IsSubtype(obj_type, &PyList_Type) ||
    	PyType_IsSubtype(obj_type, &PyDict_Type) ||
    	PyType_IsSubtype(obj_type, &PySet_Type);

    bool has_slots = PyMapping_HasKeyString(obj_type->tp_dict, "__slots__");

    // This should only work on lists, dicts or sets or have slots
    if (!is_builtin_container && !has_slots)
    {
    	PyErr_Format(PyExc_TypeError,
          "_set_class_on_builtin_or_slots can only be called on mutable container types (list, set, dict) or types with __slots__. Got '%s'",
          object->ob_type->tp_name);
    	return NULL;
    }

    // reflect instance dict and weaklist behavior onto new_type.
    // we need to do this to avoid segfaults in attribute lookup / deallocation
    // it is fine to modify the new type like this since it is a dynamically type created in `freeze`
    // and the instance is immutable afterward
	new_class_tp->tp_dictoffset = obj_type->tp_dictoffset;
	new_class_tp->tp_weaklistoffset = obj_type->tp_weaklistoffset;

#if PY_VERSION_HEX >= 0x030B0000
	// MANAGED_WEAKREF exists only in 3.11+
	if (new_class_tp->tp_dictoffset == 0)
	{
		new_class_tp->tp_flags &= ~Py_TPFLAGS_MANAGED_DICT;
	}
#endif
#if PY_VERSION_HEX >= 0x030C0000
	// MANAGED_WEAKREF exists only in 3.12+
	if (new_class_tp->tp_weaklistoffset == 0)
	{
		new_class_tp->tp_flags &= ~Py_TPFLAGS_MANAGED_WEAKREF;
	}
#endif

// IMMUTABLETYPE exists only in 3.10+
#if PY_VERSION_HEX >= 0x030A0000
	new_class_tp->tp_flags |= Py_TPFLAGS_IMMUTABLETYPE;
#endif

    Py_INCREF(new_class);
    Py_SET_TYPE(object, new_class_tp);
    Py_INCREF(object);
    return object;
}

static PyMethodDef Methods[] = {
    {"_set_class_on_builtin_or_slots",  _set_class_on_builtin_or_slots, METH_VARARGS,
     "Changes __class__ on a list, dict or set."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef _builtin_helpers_module = {
    PyModuleDef_HEAD_INIT,
    "_builtin_helpers",
    NULL,
    -1,
    Methods
};

PyMODINIT_FUNC
PyInit__builtin_helpers(void)
{
    return PyModule_Create(&_builtin_helpers_module);
}
