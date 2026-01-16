use numpy::{PyArray1, PyArray2};
use pyo3::prelude::*;

#[pyclass(module = "riichienv._riichienv")]
pub struct Y47Turn {
    #[pyo3(get)]
    pub token_main: Py<PyArray2<i64>>,
    #[pyo3(get)]
    pub token_scalar: Py<PyArray2<f32>>,
    #[pyo3(get)]
    pub token_mask: Py<PyArray1<bool>>,
    #[pyo3(get)]
    pub action_main: Py<PyArray2<i64>>,
    #[pyo3(get)]
    pub action_consume: Py<PyArray2<i64>>,
    #[pyo3(get)]
    pub action_consume_mask: Py<PyArray2<bool>>,
    #[pyo3(get)]
    pub legal_action_mask: Py<PyArray1<bool>>,
}

#[pymethods]
impl Y47Turn {
    #[new]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        token_main: Py<PyArray2<i64>>,
        token_scalar: Py<PyArray2<f32>>,
        token_mask: Py<PyArray1<bool>>,
        action_main: Py<PyArray2<i64>>,
        action_consume: Py<PyArray2<i64>>,
        action_consume_mask: Py<PyArray2<bool>>,
        legal_action_mask: Py<PyArray1<bool>>,
    ) -> Self {
        Self {
            token_main,
            token_scalar,
            token_mask,
            action_main,
            action_consume,
            action_consume_mask,
            legal_action_mask,
        }
    }
}
