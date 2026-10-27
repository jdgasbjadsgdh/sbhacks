"""Screen-coordinate layout shared by drawing and mouse hit testing."""


def panel_layout(width, height, requested=0, dpi=1, reserve=0):
    height -= max(0,reserve)
    if width < 300 or height < 340:
        return None
    scale = requested if requested > 0 else max(1, dpi, height/1080)
    scale = min(max(1, scale), 3, max(1, (width-24)/360), max(1, (height-24)/360))
    pad = round(12*scale)
    w, h = min(round(448*scale), width-24), min(round(500*scale), height-24)
    x, y = width-w-12, max(12, min(round(150*scale), height-h-12))
    compact = h < 470*scale
    header, footer = round(78*scale), round((96 if compact else 182)*scale)
    pitch = (h-header-footer)/4
    half = (w-3*pad)//2
    bh = min(round(34*scale), round(pitch-19*scale))
    buttons = [(x+pad+(i%2)*(half+pad), round(y+header+(i//2)*pitch), half, bh) for i in range(8)]
    sw = round(28*scale)
    sizes = [(x+w-pad-2*sw-4, y+pad, sw, round(25*scale)), (x+w-pad-sw, y+pad, sw, round(25*scale))]
    result = dict(panel=(x,y,w,h), buttons=buttons, tab=(max(12,width-round(270*scale)-12),y,round(270*scale),round(32*scale)),
                sizes=sizes, scale=scale, pad=pad, compact=compact, footer=y+h-footer, pitch=pitch)

    result['all']=(x+pad,round(y+h-footer+2*scale),w-2*pad,round(23*scale))
    result['keys']=(x+w-pad-2*sw-8-round(54*scale),y+pad,round(54*scale),round(25*scale))
    return result
