# adptvgrnMod

This combines kagefunc's adaptive_grain function with havsfunc's GrainFactory3 port to introduce additional size and sharpness parameters, as well as the option to only add grain to the luma plane. YUV input is required.

## Usage

```python
adptvgrnMod(clip_in, strength=0.25, size=1, sharp=50, static=True, luma_scaling=12, grain_chroma=True, grainer=None, show_mask=False)
```

**strength**
Strength of the grain generated by AddGrain.

**size**
Size of grain. Bicubic resizing is used.

**sharp**
Sharpness to use when upscaling the grain to size.

**static**
Whether to generate static or dynamic grain.

**luma_scaling**
This values changes the general grain opacity curve. Lower values will generate more grain, even in brighter scenes, while higher values will generate less, even in dark scenes. 

**grain_chroma**
Whether grain should be added to chroma planes.

**grainer**
Option to allow use of alternative graining functions.

**show_mask**
Whether to show generated mask.

## FrameType and frmtpgrn

These are wrappers to allow one to use different adptvgrnMod parameters for different picture types.