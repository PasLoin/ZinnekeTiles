from ..density import poi_rank_filter, poi_sort_key
from ..expressions import zoom
from ..palette import palette


def poi(cfg, pal=None):
    pal = pal or palette({}, "poi")
    fc = cfg["color"] or "#734a08"
    ap = cfg["appear_at"]
    la = cfg["labels_at"]
    d  = cfg.get("density")
    dots = max(ap, d.get("dots_at", ap)) if d else ap
    circle = {"id":"poi-circle","type":"circle",
         "source":"poi","source-layer":"poi","minzoom":dots,
         "paint":{"circle-radius":zoom([(dots,2),(18,4)]),
                  "circle-color":fc,
                  "circle-stroke-color":pal["stroke"],"circle-stroke-width":.8,
                  "circle-opacity":.85}}
    if d and d.get("overlap_at") is not None:
        overlap = ["step",["zoom"],False,d["overlap_at"],True]
    else:
        overlap = not d
    layout = {
             "icon-image":["coalesce",
                 ["case",["==",["get","cuisine"],"friture"],
                         ["image","poi-cuisine-friture"],["image",""]],
                 ["image",["concat","poi-",["get","shop"]]],
                 ["image",["concat","poi-",["get","amenity"]]],
                 ["image",["concat","poi-",["get","tourism"]]],
                 ["image",["concat","poi-",["get","leisure"]]],
                 ["image",["concat","poi-",["get","emergency"]]],
                 ["image",["concat","poi-",["get","healthcare"]]],
                 ["image",["concat","poi-",["get","office"]]],
                 ["image",["concat","poi-",["get","historic"]]],
                 ["case",["has","shop"],["image","poi-shop"],["image",""]]],
             "icon-size":zoom([(ap,.7),(18,1.0)]),
             "icon-allow-overlap":overlap,"icon-padding":2,"icon-anchor":"center",
             "text-field":["step",["zoom"],"",la,["get","name"]],
             "text-font":["Noto Sans Regular"],"text-size":10,
             "text-offset":[0,1.2],"text-anchor":"top","text-optional":True}
    if d:
        layout["symbol-sort-key"] = poi_sort_key(d)
    icon = {"id":"poi-icon","type":"symbol",
         "source":"poi","source-layer":"poi","minzoom":ap}
    rank_filter = poi_rank_filter(d) if d else None
    if rank_filter:
        icon["filter"] = rank_filter
    icon["layout"] = layout
    icon["paint"] = {"icon-opacity":.9,"text-color":fc,
                     "text-halo-color":pal["label_halo"],"text-halo-width":1.2}
    return [
        circle,
        icon,
        {"id":"leisure-icon","type":"symbol",
         "source":"leisure","source-layer":"leisure","minzoom":ap,
         "filter":["!=",["get","leisure"],"playground"],
         "layout":{
             "icon-padding":50,"symbol-placement":"point","icon-allow-overlap":False,
             "icon-image":["coalesce",
                 ["case",["==",["get","cuisine"],"friture"],
                         ["image","poi-cuisine-friture"],["image",""]],
                 ["image",["concat","poi-",["get","shop"]]],
                 ["image",["concat","poi-",["get","amenity"]]],
                 ["image",["concat","poi-",["get","tourism"]]],
                 ["case",["has","shop"],["image","poi-shop"],["image",""]]],
             "icon-size":zoom([(ap,.7),(18,1.0)]),
             "icon-ignore-placement":False,"icon-anchor":"center",
             "text-field":["step",["zoom"],"",la,["get","name"]],
             "text-font":["Noto Sans Regular"],"text-size":10,
             "text-offset":[0,1.2],"text-anchor":"top","text-optional":True},
         "paint":{"icon-opacity":.9,"text-color":fc,
                  "text-halo-color":pal["label_halo"],"text-halo-width":1.2}},
    ]
