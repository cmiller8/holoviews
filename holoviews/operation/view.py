import numpy as np

import param

from ..core import Dimension, ViewOperation, Overlay
from ..core.options import options
from ..core.util import find_minmax
from ..view import ItemTable, Matrix, VectorField, Contours, Histogram


class chain(ViewOperation):
    """
    Definining a viewoperation chain is an easy way to define a new
    ViewOperation from a series of existing ones. The single argument
    is a callable that accepts an input view and returns a list of
    output views. To create the custom ViewOperation, you will need to
    supply this argument to a new instance of chain. For example:

    chain.instance(chain=lambda x: [cmap2rgb(operator(x).N, cmap='jet')])

    This is now a ViewOperation that sums the data in the input
    overlay and turns it into an RGB Matrix with the 'jet'
    colormap.
    """

    chain = param.Callable(doc="""A chain of existing ViewOperations.""")

    def _process(self, view, key=None):
        return self.p.chain(view)


class operator(ViewOperation):
    """
    Applies any arbitrary operator on the data (currently only
    supports Matrix views) and returns the result.
    """

    operator = param.Callable(np.add, doc="""
        The commutative operator to apply between the data attributes
        of the supplied Views. By default, performs elementwise
        addition across the Matrix arrays.""")

    unpack = param.Boolean(default=True, doc=""" Whether the operator
       is supplied the .data attributes as an unpack collection of
       arguments or as a list.""")

    label = param.String(default='Operation', doc="""
        The label for the result after having applied the operator.""")


    def _process(self, overlay, key=None):

        if not isinstance(overlay, Overlay):
            raise Exception("Operation requires an Overlay as input")

        if self.p.unpack:
            new_data = self.p.operator(*[el.data for el in overlay])
        else:
            new_data = self.p.operator([el.data for el in overlay])

        return [Matrix(new_data, bounds=overlay[0].bounds, label=self.p.label,
                            roi_bounds=overlay[0].roi_bounds)]


class convolve(ViewOperation):
    """
    Apply a convolution to an overlay using the top layer as the
    kernel used to convolve the bottom layer. Both input Matrix
    elements in the overlay should be single-channel.
    """

    label = param.String(default='Convolution', doc="""
        The label to identify the output of the Convolution.""")

    kernel_roi = param.NumericTuple(default=(0,0,0,0), length=4, doc="""
        A 2-dimensional slice of the kernel layer to use in the
        convolution in lbrt (left, bottom, right, top) format. By
        default, no slicing is applied.""")

    def _process(self, view, key=None):

        if len(view) != 2:
            raise Exception("Overlay of two layers required.")

        [target, kernel] = view[0], view[1]

        if len(target.data.shape) != 2:
            raise Exception("Convolve requires monochrome inputs.")

        xslice = slice(self.p.kernel_roi[0], self.p.kernel_roi[2])
        yslice = slice(self.p.kernel_roi[1], self.p.kernel_roi[3])

        k = kernel.data if self.p.kernel_roi == (0,0,0,0) else kernel[xslice, yslice].data

        fft1 = np.fft.fft2(target.data)
        fft2 = np.fft.fft2(k, s= target.data.shape)
        convolved_raw = np.fft.ifft2(fft1 * fft2).real

        k_rows, k_cols = k.shape
        rolled = np.roll(np.roll(convolved_raw, -(k_cols//2), axis=-1), -(k_rows//2), axis=-2)
        convolved = rolled / float(k.sum())

        return [Matrix(convolved, bounds=target.bounds)]


class contours(ViewOperation):
    """
    Given a Matrix with a single channel, annotate it with contour
    lines for a given set of contour levels.

    The return is a overlay with a Contours layer for each given
    level, overlaid on top of the input Matrix.
    """

    levels = param.NumericTuple(default=(0.5,), doc="""
         A list of scalar values used to specify the contour levels.""")

    label = param.String(default='Level', doc="""
      The label suffix used to label the resulting contour curves
      where the suffix is added to the label of the  input Matrix""")

    def _process(self, sheetview, key=None):
        from matplotlib import pyplot as plt

        figure_handle = plt.figure()
        (l, b, r, t) = sheetview.lbrt
        contour_set = plt.contour(sheetview.data, extent=(l, r, t, b),
                                  levels=self.p.levels)

        contours = []
        for level, cset in zip(self.p.levels, contour_set.collections):
            paths = cset.get_paths()
            lines = [path.vertices for path in paths]
            contours.append(Contours(lines, label=sheetview.label + ' ' + self.p.label))

        plt.close(figure_handle)

        if len(contours) == 1:
            return [(sheetview * contours[0])]
        else:
            return [sheetview * Overlay(contours)]


class histogram(ViewOperation):
    """
    Returns a Histogram of the Raster data, binned into
    num_bins over the bin_range (if specified).

    If adjoin is True, the histogram will be returned adjoined to
    the Raster as a side-plot.
    """

    adjoin = param.Boolean(default=True, doc="""
      Whether to adjoin the histogram to the View.""")

    bin_range = param.NumericTuple(default=(0, 0), doc="""
      Specifies the range within which to compute the bins.""")

    dimension = param.String(default=None, doc="""
      Along which dimension of the View to compute the histogram.""")

    normed = param.Boolean(default=True, doc="""
      Whether the histogram frequencies are normalized.""")

    individually = param.Boolean(default=True, doc="""
      Specifies whether the histogram will be rescaled for each Raster in a Map.""")

    num_bins = param.Integer(default=20, doc="""
      Number of bins in the histogram .""")

    style_prefix = param.String(default=None, allow_None=None, doc="""
      Used for setting a common style for histograms in a ViewMap or AdjointLayout.""")

    def _process(self, view, key=None):
        data = np.array(view.dim_values(self.p.dimension if self.p.dimension else view.value.name))
        range = find_minmax((np.min(data), np.max(data)), (0, -float('inf')))\
            if self.p.bin_range is None else self.p.bin_range

        # Avoids range issues including zero bin range and empty bins
        if range == (0, 0):
            range = (0.0, 0.1)
        try:
            data = data[np.invert(np.isnan(data))]
            hist, edges = np.histogram(data, normed=self.p.normed,
                                       range=range, bins=self.p.num_bins)
        except:
            edges = np.linspace(range[0], range[1], self.p.num_bins + 1)
            hist = np.zeros(self.p.num_bins)
        hist[np.isnan(hist)] = 0

        hist_view = Histogram(hist, edges, dimensions=[view.value],
                              label=view.label, value='Frequency')

        # Set plot and style options
        style_prefix = self.p.style_prefix if self.p.style_prefix else \
            'Custom[<' + self.name + '>]_'
        opts_name = style_prefix + hist_view.label.replace(' ', '_')
        hist_view.style = opts_name
        options[opts_name] = options.plotting(view)(
            **dict(rescale_individually=self.p.individually))
        return [(view << hist_view) if self.p.adjoin else hist_view]



class vectorfield(ViewOperation):
    """
    Given a Matrix with a single channel, convert it to a
    VectorField object at a given spatial sampling interval. The
    values in the Matrix are assumed to correspond to the vector
    angle in radians and the value is assumed to be cyclic.

    If supplied with an overlay, the second sheetview in the overlay
    will be interpreted as the third vector dimension.
    """

    rows = param.Integer(default=10, doc="""
         Number of rows in the vector field.""")

    cols = param.Integer(default=10, doc="""
         Number of columns in the vector field.""")

    label = param.String(default='Vectors', doc="""
      The label suffix used to label the resulting vector field
      where the suffix is added to the label of the  input Matrix""")


    def _process(self, view, key=None):

        if isinstance(view, Overlay) and len(view) >= 2:
            radians, lengths = view[0], view[1]
        else:
            radians, lengths = view, None

        if not radians.value.cyclic:
            raise Exception("First input Matrix must be declared cyclic")

        l, b, r, t = radians.bounds.lbrt()
        X, Y = np.meshgrid(np.linspace(l, r, self.p.cols+2)[1:-1],
                           np.linspace(b, t, self.p.rows+2)[1:-1])

        vector_data = []
        for x, y in zip(X.flat, Y.flat):

            components = (x,y, radians[x,y])
            if lengths is not None:
                components += (lengths[x,y],)

            vector_data.append(components)

        value_dimension = Dimension('VectorField', cyclic=True, range=radians.range)
        return [VectorField(vector_data,
                            label=radians.label + ' ' + self.p.label,
                            value=value_dimension)]


class threshold(ViewOperation):
    """
    Threshold a given Matrix at a given level into the specified
    low and high values.  """

    level = param.Number(default=0.5, doc="""
       The value at which the threshold is applied. Values lower than
       the threshold map to the 'low' value and values above map to
       the 'high' value.""")

    high = param.Number(default=1.0, doc="""
      The value given to elements greater than (or equal to) the
      threshold.""")

    low = param.Number(default=0.0, doc="""
      The value given to elements below the threshold.""")

    label = param.String(default='Thresholded', doc="""
       The label suffix used to label the resulting sheetview where
       the suffix is added to the label of the input Matrix""")

    def _process(self, view, key=None):
        arr = view.data
        high = np.ones(arr.shape) * self.p.high
        low = np.ones(arr.shape) * self.p.low
        thresholded = np.where(arr > self.p.level, high, low)

        return [Matrix(thresholded,
                          label=view.label + ' ' + self.p.label)]


class roi_table(ViewOperation):
    """
    Compute a table of information from a Matrix within the
    indicated region-of-interest (ROI). The function applied must
    accept a numpy array and return either a single value or a
    dictionary of values which is returned as a ItemTable or ViewMap.

    The roi is specified using a boolean Matrix overlay (e.g as
    generated by threshold) where zero values are excluded from the
    ROI.
    """

    fn = param.Callable(default=np.mean, doc="""
        The function that is applied within the mask area to supply
        the relevant information. Other valid examples include np.sum,
        np.median, np.std etc.""")

    heading = param.String(default='result', doc="""
       If the output of the function is not a dictionary, this is the
       label given to the resulting value.""")

    label = param.String(default='ROI', doc="""
       The label suffix that labels the resulting table where this
       suffix is added to the label of the input data Matrix""")


    def _process(self, view, key=None):

        if not isinstance(view, Overlay) or len(view) != 2:
            raise Exception("A Overlay of two SheetViews is required.")

        mview, mask = view[0], view[1]

        if mview.data.shape != mask.data.shape:
            raise Exception("The data array shape of the mask layer"
                            " must match that of the data layer.")

        bit_mask = mask.data.astype(np.bool)
        roi = mview.data[bit_mask]

        if len(roi) == 0:
            raise Exception("No region of interest defined in ROI mask" )

        results = self.p.fn(roi)
        if not isinstance(results, dict):
            results = {self.p.heading:results}

        return [ItemTable(results, label=mview.label + ' ' + self.p.label)]