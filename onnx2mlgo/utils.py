from typing import List
from graph import Graph
import re
import custom_types

def indent_lines(code_list: custom_types.Statement, space_size: int, tabs: bool = False):
  """Formats a `code_list` into a single string where each line is on a new line.\
Each line has `space_size` spaces before each line. Doesn't add a new line to the\
last line of code.

  Args:
      code_list (types.Statement): Each element represents a line of code
      space_size (_type_): Size of spacing before each line
  """
  output = ""
  spacing = ' ' * space_size
  for i in range(len(code_list)):
    new_line = '\n' if i != (len(code_list)-1) else ''
    output += f'{spacing}{code_list[i]}{new_line}'
  return output

def sanitize_string(string: str):
  """Sanitizes `string` so that it's a valid Go variable name 

  Args:
      string (str): Input string

  Returns:
      _type_: Sanitized string 
  """
  string = string.replace('.','_')
  string = string.replace('/','_')
  return string

def sanitize_list(input: List[str]):
  """Sanitizes `input` list so all elements are valid Go variable names

  Args:
      input (List[str]): 

  Returns:
      _type_: Sanitized string
  """
  return list(map(sanitize_string, input))

def create_single_layer(var_name: str, mlgo_op: str, input_list) -> str:
  """Creates a single MLGO operation.
  
  e.g. var_name = output, mlgo_op = MulMat, input_list = [tensor1, tensor2]
  -> output := ml.MulMat(ctx0, tensor1, tensor2)

  Args:
      var_name (str): Variable name of output tensor
      mlgo_op (str): Name of MLGO op (e.g. MulMat, Add, Relu)
      input_list (_type_): List of variable names of input tensors

  Returns:
      str: Output line of Go code
  """
  # TODO: check whether the number of inputs are valid for the given mlgo_op
  input_str = ', '.join(input_list)
  return f'{var_name} := ml.{mlgo_op}(ctx0, {input_str})'

def create_layers(graph: Graph) -> custom_types.Statement:
  """Creates a list of MLGO operations.

  Args:
      graph (Graph): MLGO graph

  Returns:
      custom_types.Statement: Output lines of Go code.
  """
  output: custom_types.Statement = []
  # TODO: extend this for multi-path graphs
  for node in graph.nodes:
    output.append(create_single_layer(node.output, node.op, node.inputs))
  # assert : output is a list of go language lines for the defining layers of the nn
  return output

def shape_size(tensor_variant: custom_types.TensorVariant):
  """Get the shape size of a tensor from it's tensor_variant
  
  e.g. NewTensor2D has shape size 2, NewTensor4D has shape size 4

  Args:
      tensor_variant (custom_types.TensorVariant)

  Returns:
      _type_
  """
  number = re.search(r'\d+', tensor_variant)
  if number:
    return int(number.group())
  else:
    raise ValueError(f'tensor variant ({tensor_variant}) does not indicate shape size')

def define_tensor(var_name: str,
                  tensor_variant: custom_types.TensorVariant,
                  ctx: str,
                  dtype: custom_types.Dtype,
                  shape: List[int]):
  """Create Go tensor definition
  
  e.g. var_name = out, tensor_variant = NewTensor1D, ctx = ctx0, dtype = TYPE_F32, shape = [3, 10]
  -> 
  out := ml.NewTensor1D(ctx0, ml.TYPE_F32, uint32(3), uint32(10))

  Args:
      var_name (str)
      tensor_variant (custom_types.TensorVariant)
      ctx (str)
      dtype (custom_types.Dtype)
      shape (List[int])

  Returns:
      _type_
  """
  shape_argument = ', '.join([f'uint32({dim})' for dim in shape])
  if shape_size(tensor_variant) != len(shape):
    raise ValueError(f'shape size ({len(shape)}) does not match tensor variant ({tensor_variant})')
  return [f'{var_name} := ml.{tensor_variant}({ctx}, ml.{dtype}, {shape_argument})']

def create_for_loop(
  init_statement: custom_types.Statement,
  condition_statement: custom_types.Statement,
  post_statement: custom_types.Statement,
  loop_statements: List[custom_types.Statement]
) -> custom_types.Statement:
  """Creates Go for loop

  Args:
      init_statement (custom_types.Statement)
      condition_statement (custom_types.Statement)
      post_statement (custom_types.Statement)
      loop_statements (List[custom_types.Statement])

  Returns:
      custom_types.Statement
  """
  return [f'for {init_statement}; {condition_statement}; {post_statement} {{',
          f'{indent_lines(loop_statements, 2)}',
          f'}}']

def initialize_tensor(loop_var: str, tensor_var_name: str, filename: str = '') -> custom_types.Statement:
  # TODO: create a codegen library for go
  # TODO: remove the {loop_var} param and replace it with a function that finds a loop_var not currently in use
  """Creates tensor initialization Go statements 

  Args:
      loop_var (str)
      tensor_var_name (str)
      filename (str, optional). Defaults to ''.

  Returns:
      custom_types.Statement: _description_
  """
  return create_for_loop(f'{loop_var} := 0', f'{loop_var} < len({tensor_var_name}.Data)', f'{loop_var}++',
                         [f'{tensor_var_name}.Data[{loop_var}] = readFP32(file)'])

tensor_variants = {
    1: 'NewTensor1D',
    2: 'NewTensor2D',
    3: 'NewTensor3D',
    4: 'NewTensor4D'
}

def define_and_initialize_tensors(graph: Graph) -> custom_types.Statement:
  output = []
  # TODO: there are ml.NewTensor2DWithData type tensors. see if you can integrate them
  for initializer in graph.initializers:
    name = sanitize_string(initializer.name)
    dims_length = len(initializer.dims)
    if dims_length in tensor_variants:
      tensor_variant = tensor_variants[dims_length]
    else:
      raise Exception(f'number of dims ({initializer.dims}) does not fit any tensor_variant')
    # TODO: initializer.dims[::-1] is a hack. might fail on some models. fix this.
    output += define_tensor(name, tensor_variant, 'nil', 'TYPE_F32', initializer.dims[::-1])
    output += initialize_tensor('i', name)
    output.append('') # new line
  for input in graph.inputs:
    name = sanitize_string(input.name)
    x = filter(lambda x: type(x.dim_value) is int, input.type.tensor_type.shape.dim)
    shape = str(input.type.tensor_type.shape.dim)
    input_dims = [int(s) for s in shape.split() if s.isdigit()]
    dims_length = len(input_dims)
    if dims_length in tensor_variants:
      tensor_variant = tensor_variants[dims_length]
    else:
      raise Exception(f'number of dims ({input_dims}) does not fit any tensor_variant')
    output += define_tensor(name, tensor_variant, 'nil', 'TYPE_F32', input_dims)
  # assert : output is a list of go language lines for defining and initializing the input and weight tensors
  return output

def get_assignment_target(line: str):
  return line.partition(':=')[0].strip()