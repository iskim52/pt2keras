import logging

from tensorflow import keras

from ..graph import OnnxNode
from .common import converter


@converter('GlobalAveragePool')
def global_average_pool(node: OnnxNode, _, input_tensor):
    try:
        # keepdims available in TF > 2.6.0.
        output_layer = keras.layers.GlobalAveragePooling2D(keepdims=True)
        output = output_layer(input_tensor)
    except TypeError:
        # Fallback. TF version < 2.6.0
        output_layer = keras.Sequential(
            [keras.layers.GlobalAveragePooling2D(), keras.layers.Reshape((1, 1, input_tensor.shape[-1]))]
        )
        # Here, an error is thrown
        output = output_layer(input_tensor)
    return output, output_layer


@converter('MaxPool')
def max_pool(node: OnnxNode, input_layer, _):

    attributes = node.attributes
    logger = logging.getLogger('onnx:max_pool')
    kernel_shape = attributes['kernel_shape']
    stride_shape = attributes['strides']
    pads = attributes['pads'] if 'pads' in attributes else [0, 0, 0, 0, 0, 0]
    pad = 'valid'

    logger.debug(f'MaxPool input layer: {input_layer}\n\n. Input tensor: {input_layer}')

    if (
        all([shape % 2 == 1 for shape in kernel_shape])
        and all([kernel_shape[i] // 2 == pads[i] for i in range(len(kernel_shape))])
        and all([shape == 1 for shape in stride_shape])
    ):
        pad = 'same'
        logger.debug('Use `same` padding parameters.')
    else:
        logger.debug('Unable to use `same` padding. Add ZeroPadding2D layer to fix shapes.')
        padding_name = node.name + '_pad'
        if len(kernel_shape) == 2:
            padding = None

            if len(pads) == 2 and (pads[0] > 0 or pads[1] > 0):
                padding = (pads[0], pads[1])
            elif len(pads) == 4 and (pads[0] > 0 or pads[1] > 0 or pads[2] > 0 or pads[3] > 0):
                padding = ((pads[0], pads[2]), (pads[1], pads[3]))

            if padding is not None:
                padding_layer = keras.layers.ZeroPadding2D(padding=padding, name=padding_name)
                input_layer = padding_layer(input_layer)
        else:  # 3D padding
            padding_layer = keras.layers.ZeroPadding3D(padding=pads[: len(stride_shape)], name=padding_name)
            input_layer = padding_layer(input_layer)

    if len(kernel_shape) == 2:
        pooling = keras.layers.MaxPooling2D(
            pool_size=kernel_shape,
            strides=stride_shape,
            padding=pad,
        )
    elif len(kernel_shape) == 3:
        pooling = keras.layers.MaxPooling3D(
            pool_size=kernel_shape,
            strides=stride_shape,
            padding=pad,
        )
    else:
        raise ValueError('Pooling operation must be performed on 2D or 3D objects')

    return pooling(input_layer), pooling


@converter('AveragePool')
def average_pool(node: OnnxNode, input_layer, _):

    attributes = node.attributes
    logger = logging.getLogger('onnx::average_pool')

    kernel_shape = attributes['kernel_shape']
    stride_shape = attributes['strides']

    pads = attributes['pads'] if 'pads' in attributes else [0, 0, 0, 0, 0, 0]
    pad = 'valid'

    if (
        all([shape % 2 == 1 for shape in kernel_shape])
        and all([kernel_shape[i] // 2 == pads[i] for i in range(len(kernel_shape))])
        and all([shape == 1 for shape in stride_shape])
    ):
        pad = 'same'
        logger.warning('Use `same` padding.')
    else:
        logger.warning('Unable to use `same` padding. Add ZeroPadding2D layer to fix shapes.')
        padding_name = f'{node.name}_pad'
        if len(kernel_shape) == 2:
            padding_layer = keras.layers.ZeroPadding2D(padding=pads[: len(stride_shape)], name=padding_name)
        else:  # 3D padding
            padding_layer = keras.layers.ZeroPadding3D(padding=pads[: len(stride_shape)], name=padding_name)
        input_layer = padding_layer(input_layer)
    if len(kernel_shape) == 2:
        pooling = keras.layers.AveragePooling2D(
            pool_size=kernel_shape,
            strides=stride_shape,
            padding=pad,
            name=f'{node.name}_average_pooling',
        )
    else:
        pooling = keras.layers.AveragePooling3D(
            pool_size=kernel_shape,
            strides=stride_shape,
            padding=pad,
            name=f'{node.name}_average_pooling',
        )
    output = pooling(input_layer)
    return output, pooling
