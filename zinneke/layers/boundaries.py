def boundaries(cfg):
    return [{"id":"boundaries","type":"line",
        "source":"boundaries","source-layer":"boundaries","minzoom":cfg["appear_at"],
        "paint":{"line-color":cfg["color"] or "#ac46ac","line-width":1,
                 "line-dasharray":[5,5],"line-opacity":.7}}]
