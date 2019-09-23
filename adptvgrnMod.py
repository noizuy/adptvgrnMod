from vapoursynth import core
import vapoursynth as vs
from vsutil import get_depth, get_y, split, plane
import fvsfunc as fvf
import numpy as np
import math
from functools import partial


def adptvgrnMod(clip_in: vs.VideoNode, strength=0.25, size=1, sharp=50, static=True, luma_scaling=12, grain_chroma=True,
                grainer=None, show_mask=False) -> vs.VideoNode:
    """
    Original header:
    Generates grain based on frame and pixel brightness. Details can be found here:
    https://kageru.moe/blog/article/adaptivegrain
    Strength is the strength of the grain generated by AddGrain, static=True for static grain, luma_scaling
    manipulates the grain alpha curve. Higher values will generate less grain (especially in brighter scenes),
    while lower values will generate more grain, even in brighter scenes.
    ====================================================================================================================
    This mod simply adds the size and sharpness features from havsfunc's GrainFactory3.
    Additionally, the option to process only luma is added. Requires YUV input.
    New:
    - Option to add your own graining function (i.e. grainer=lambda x: core.f3kdb.Deband(x, y=0, cr=0, cb=0, grainy=64,
      dynamic_grain=True, keep_tv_range=True, output_depth=16)
    """

    def m4(x):
        return 16 if x < 16 else math.floor(x / 4 + 0.5) * 4

    neutral = 1 << (get_depth(clip_in) - 1)
    if grain_chroma == False and clip_in.format.color_family == vs.YUV:
        clip = plane(clip_in, 0)
        u = plane(clip_in, 1)
        v = plane(clip_in, 2)
    elif grain_chroma == False and clip_in.format.color_family != vs.YUV:
        raise ValueError("Not graining chroma is only possible with YUV input at this time.")
    else:
        clip = clip_in

    def fill_lut(y):
        """
        Using horner's method to compute this polynomial:
        (1 - (1.124 * x - 9.466 * x² + 36.624 * x³ - 45.47 * x⁴ + 18.188 * x⁵)) ** ((y²) * luma_scaling) * 255
        Using the normal polynomial is about 2.5x slower during the initial generation.
        I know it doesn't matter as it only saves a few ms (or seconds at most), but god damn, just let me have
        some fun here, will ya? Just truncating (rather than rounding) the array would also half the processing
        time, but that would decrease the precision and is also just unnecessary.
        """
        x = np.arange(0, 1, 1 / (1 << 8))
        z = (1 - (x * (1.124 + x * (-9.466 + x * (36.624 + x * (-45.47 + x * 18.188)))))) ** ((y ** 2) * luma_scaling)
        if clip.format.sample_type == vs.INTEGER:
            z = z * 255
            z = np.rint(z).astype(int)
        return z.tolist()

    lut = [None] * 1000
    for y in np.arange(0, 1, 0.001):
        lut[int(round(y * 1000))] = fill_lut(y)

    def generate_mask(n, f, clip):
        frameluma = round(f.props.PlaneStatsAverage * 999)
        table = lut[int(frameluma)]
        return core.std.Lut(clip, lut=table)

    cw = clip.width  # ox
    ch = clip.height  # oy
    sx = m4(cw / size)
    sy = m4(ch / size)
    sxa = m4((cw + sx) / 2)
    sya = m4((ch + sy) / 2)
    b = sharp / -50 + 1
    c = (1 - b) / 2

    luma = get_y(fvf.Depth(clip_in, 8)).std.PlaneStats()
    blank = core.std.BlankClip(clip, sx, sy, color=[neutral for i in split(clip)])
    if grainer == None:
        grained = core.grain.Add(blank, var=strength, constant=static)
    else:
        grained = grainer(blank)
    if size != 1 and (sx != cw or sy != ch):
        if size > 1.5:
            grained = core.resize.Bicubic(grained, sxa, sya, filter_param_a=b, filter_param_b=c)
            grained = core.resize.Bicubic(grained, cw, ch, filter_param_a=b, filter_param_b=c)
        else:
            grained = core.resize.Bicubic(grained, cw, ch, filter_param_a=b, filter_param_b=c)

    grained = core.std.MakeDiff(clip, grained)

    if grain_chroma == False and clip_in.format.color_family == vs.YUV:
        grained = core.std.ShufflePlanes([grained, u, v], [0, 0, 0], clip_in.format.color_family)

    mask = core.std.FrameEval(luma, partial(generate_mask, clip=luma), prop_src=luma)
    mask = core.resize.Spline36(mask, cw, ch)

    if get_depth(clip) != 8:
        mask = fvf.Depth(mask, bits=get_depth(clip))
    if show_mask:
        return mask

    return core.std.MaskedMerge(clip_in, grained, mask)


def FrameType(n, clip, funcB=lambda x: x, funcP=lambda x: x, funcI=lambda x: x):
    if clip.get_frame(n).props._PictType.decode() == "B":
        return funcB(clip)
    elif clip.get_frame(n).props._PictType.decode() == "P":
        return funcP(clip)
    else:
        return funcI(clip)


def frmtpgrn(clip: vs.VideoNode, bstrength=0.25, bsize=1, bsharp=50, bstatic=True, bluma_scaling=12, bgrain_chroma=True,
             bgrainer=None,
             bshow_mask=False, pstrength=None, psize=None, psharp=None, pstatic=None, pluma_scaling=None,
             pgrain_chroma=None, pgrainer=None,
             pshow_mask=None, istrength=None, isize=None, isharp=None, istatic=None, iluma_scaling=None,
             igrain_chroma=None, igrainer=None,
             ishow_mask=None) -> vs.VideoNode:
    """
    Use different adptvgrnMod functions on different picture types.
    """
    if pstrength == None:
        pstrength = bstrength * 0.8
    if psize == None:
        psize = bsize
    if psharp == None:
        psharp = bsharp
    if pstatic == None:
        pstatic = bstatic
    if pluma_scaling == None:
        pluma_scaling = bluma_scaling
    if pgrain_chroma == None:
        pgrain_chroma = bgrain_chroma
    if pgrainer == None:
        pgrainer = bgrainer
    if pshow_mask == None:
        pshow_mask = bshow_mask
    if istrength == None:
        istrength = pstrength * 0.5
    if isize == None:
        isize = psize
    if isharp == None:
        isharp = psharp
    if istatic == None:
        istatic = pstatic
    if iluma_scaling == None:
        iluma_scaling = pluma_scaling
    if igrain_chroma == None:
        igrain_chroma = pgrain_chroma
    if igrainer == None:
        igrainer = pgrainer
    if ishow_mask == None:
        ishow_mask = pshow_mask

    return core.std.FrameEval(clip, partial(FrameType, clip=clip,
                                            funcB=lambda x: adptvgrnMod(x, strength=bstrength, size=bsize, sharp=bsize,
                                                                        static=bstatic, luma_scaling=bluma_scaling,
                                                                        grain_chroma=bgrain_chroma, grainer=bgrainer,
                                                                        show_mask=bshow_mask),
                                            funcP=lambda x: adptvgrnMod(x, strength=pstrength, size=psize, sharp=psize,
                                                                        static=pstatic, luma_scaling=pluma_scaling,
                                                                        grain_chroma=pgrain_chroma, grainer=pgrainer,
                                                                        show_mask=pshow_mask),
                                            funcI=lambda x: adptvgrnMod(x, strength=istrength, size=isize, sharp=isize,
                                                                        static=istatic, luma_scaling=iluma_scaling,
                                                                        grain_chroma=igrain_chroma, grainer=igrainer,
                                                                        show_mask=ishow_mask)))
