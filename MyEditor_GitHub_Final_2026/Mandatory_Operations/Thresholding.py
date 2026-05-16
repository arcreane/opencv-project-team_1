def threshold_dialog(self):
        controls = [
            {
                "type": "choice",
                "name": "mode",
                "label": "Mode",
                "values": ["Binary", "Otsu", "Adaptive"],
                "value": "Binary",
            },
            {
                "type": "scale",
                "name": "threshold",
                "label": "Binary threshold",
                "from": 0,
                "to": 255,
                "value": 127,
            },
            {
                "type": "scale",
                "name": "block_size",
                "label": "Adaptive block size",
                "from": 3,
                "to": 99,
                "value": 15,
            },
            {
                "type": "scale",
                "name": "c_value",
                "label": "Adaptive C",
                "from": -20,
                "to": 20,
                "value": 4,
            },
        ]
