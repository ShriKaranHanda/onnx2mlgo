def create_go_boilerplate(file):
  # TODO: remove redundant imports
  file.write("""\
package main

import (
  "errors"
  "fmt"
  "math"
  "mlgo/ml"
  "os"
)

"""
  )

def create_hparams_type(file, name: str):
  # TODO: is this correct? are any variables required here?
  file.write(f"""\
type {name}_hparams struct{{
  n_input int32;
  n_hidden int32;
  n_classes int32;
}}

"""
  )

def create_model_type(file):
  pass

def create_weight_loading_func(file):
  pass

def create_eval_func(file):
  pass

def create_main_func(file):
  pass