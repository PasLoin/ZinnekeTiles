LABEL_LAYER_IDS = [
    "public_transport-label",
    "road-labels",
    "road-oneway-arrows",
    "cycleway-oneway-arrows",
    "pitch-markings",
    "poi-circle",
    "poi-icon",
    "leisure-icon",
    "street-furniture-icon",
    "address-labels",
]


def order_layers(layers):
    labels = set(LABEL_LAYER_IDS)
    ground = [
        layer for layer in layers if layer["type"] != "fill-extrusion" and layer["id"] not in labels
    ]
    extrusions = [layer for layer in layers if layer["type"] == "fill-extrusion"]
    on_top = [layer for layer in layers if layer["id"] in labels]
    return ground + extrusions + on_top, (on_top[0]["id"] if on_top else None)
