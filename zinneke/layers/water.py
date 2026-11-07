from ..colors import c
from ..expressions import zoom
from ..palette import palette


def water(cfg, pal=None):
    pal = pal or palette({}, "water")
    col = cfg["color"] or "#aad3df"
    st  = cfg["subtypes"]
    out = []
    out.append({"id":"water-fill","type":"fill",
        "source":"water","source-layer":"water",
        "filter":["all",["!=",["get","tunnel"],"culvert"],
                        ["!=",["get","tunnel"],"yes"],
                        ["!=",["get","covered"],"yes"],
                        ["==",["geometry-type"],"Polygon"]],
        "paint":{"fill-color":col}})
    wetland = st.get("wetland") or {}
    out.append({"id":"water-wetland","type":"fill",
        "source":"water","source-layer":"water",
        "filter":["all",["==",["get","natural"],"wetland"],
                        ["==",["geometry-type"],"Polygon"]],
        "paint":{"fill-color": c(wetland.get("color","#d4e2c6")),
                 "fill-opacity": wetland.get("opacity", 0.5)}})
    for ww,(w,dz) in {"river":([(10,1),(18,12)],10),"canal":([(10,1),(18,10)],10),
                       "stream":([(13,.5),(18,3)],13),"ditch":([(14,.3),(18,2)],14)}.items():
        az = (st.get(ww) or {}).get("appear_at", dz)
        out.append({"id":f"waterway-{ww}","type":"line",
            "source":"water","source-layer":"water","minzoom":az,
            "filter":["all",["==",["get","waterway"],ww],
                            ["!=",["get","tunnel"],"yes"],
                            ["!=",["get","tunnel"],"culvert"],
                            ["==",["geometry-type"],"LineString"]],
            "paint":{"line-color":col,"line-width":zoom(w)}})
    out.append({"id":"water-line","type":"line",
        "source":"water","source-layer":"water",
        "filter":["all",["!=",["get","tunnel"],"culvert"],["!=",["get","tunnel"],"yes"],
                        ["!=",["get","covered"],"yes"],["==",["geometry-type"],"Polygon"],
                        ["!",["has","waterway"]]],
        "paint":{"line-color":col,"line-width":zoom([(13,1),(18,10)])}})
    out.append({"id":"water-tunnel-casing","type":"line",
        "source":"water","source-layer":"water",
        "filter":["all",["any",["==",["get","tunnel"],"yes"],["==",["get","tunnel"],"culvert"]],
                        ["==",["geometry-type"],"LineString"]],
        "paint":{"line-color":col,"line-dasharray":[2,2],
                 "line-width":zoom([(13,1.5),(18,5)])}})
    out.append({"id":"water-tunnel-core","type":"line",
        "source":"water","source-layer":"water",
        "filter":["all",["any",["==",["get","tunnel"],"yes"],["==",["get","tunnel"],"culvert"]],
                        ["==",["geometry-type"],"LineString"]],
        "paint":{"line-color":pal["tunnel_core"],"line-opacity":0.4,
                 "line-width":zoom([(13,1),(18,4)])}})
    return out
