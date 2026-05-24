from flask import Flask, request
import urllib.parse

app = Flask(__name__)

@app.route("/ship")
def ship_view():

    ship_name = request.args.get("name", "UNKNOWN")
    mmsi = request.args.get("mmsi", "-")
    lat = request.args.get("lat", "35.4500")
    lon = request.args.get("lon", "129.3800")
    sog = request.args.get("sog", "-")
    cog = request.args.get("cog", "-")
    status = request.args.get("status", "-")
    destination = request.args.get("destination", "-")
    departure = request.args.get("departure", "-")
    eta = request.args.get("eta", "-")
    length = float(request.args.get("length", "150"))

    html = f"""
    <!DOCTYPE html>
    <html>

    <head>
        <meta charset="utf-8">

        <title>{ship_name}</title>

        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <link
            rel="stylesheet"
            href="https://unpkg.com/leaflet/dist/leaflet.css"
        />

        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>

        <style>

            body {{
                margin: 0;
                font-family: Arial, sans-serif;
            }}

            #map {{
                width: 100%;
                height: 100vh;
            }}

            .info-box {{

                position: absolute;
                top: 10px;
                left: 10px;

                z-index: 9999;

                background: white;

                padding: 14px;

                border-radius: 12px;

                box-shadow: 0 0 15px rgba(0,0,0,0.3);

                min-width: 260px;
            }}

            .title {{
                font-size: 22px;
                font-weight: bold;
                color: #004fa3;
                margin-bottom: 10px;
            }}

            .row {{
                margin-bottom: 6px;
                font-size: 14px;
            }}

        </style>
    </head>

    <body>

        <div class="info-box">

            <div class="title">
                🚢 {ship_name}
            </div>

            <div class="row">MMSI: {mmsi}</div>

            <div class="row">속도: {sog} kn</div>

            <div class="row">침로: {cog}</div>

            <div class="row">상태: {status}</div>

            <hr>

            <div class="row">출발지: {departure}</div>

            <div class="row">목적지: {destination}</div>

            <div class="row">ETA: {eta}</div>

            <hr>

            <div class="row">위도: {lat}</div>

            <div class="row">경도: {lon}</div>

        </div>

        <div id="map"></div>

        <script>

            var lat = {lat};
            var lon = {lon};

            var map = L.map('map').setView([lat, lon], 13);

            L.tileLayer(
                'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
                {{
                    attribution: 'OpenStreetMap'
                }}
            ).addTo(map);

            var shipLength = {length};

            var markerSize = 20;

if (shipLength >= 300)
    markerSize = 45;

else if (shipLength >= 250)
    markerSize = 40;

else if (shipLength >= 200)
    markerSize = 35;

else if (shipLength >= 150)
    markerSize = 30;

else if (shipLength >= 100)
    markerSize = 25;
            var shipIcon = L.divIcon({{

                className: '',

                html: `
                    <div style="
                        width: ${{markerSize}}px;
                        height: ${{markerSize}}px;

                        background: #0057d9;

                        border: 4px solid white;

                        border-radius: 50% 50% 10% 10%;

                        box-shadow: 0 0 15px rgba(0,0,0,0.55);

                        display: flex;

                        align-items: center;

                        justify-content: center;

                        font-size: ${{markerSize * 0.55}}px;

                        color: white;

                        transform: rotate({cog}deg);
                    ">
                        ▲
                    </div>
                `,

                iconSize: [markerSize, markerSize],

                iconAnchor: [
                    markerSize / 2,
                    markerSize / 2
                ]
            }});

            L.marker(
                [lat, lon],
                {{
                    icon: shipIcon
                }}
            )
            .addTo(map)
            .bindPopup(
                "<b>{ship_name}</b><br>MMSI: {mmsi}"
            )
            .openPopup();

        </script>

    </body>

    </html>
    """

    return html


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8080
    )