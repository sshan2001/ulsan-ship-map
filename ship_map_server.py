from flask import Flask, request
import json

app = Flask(__name__)

RENDER_MAP_BASE_URL = "https://ulsan-ship-map.onrender.com/ship"


def dms_to_decimal(deg, minute, sec):
    return deg + (minute / 60.0) + (sec / 3600.0)


# M묘박지 기준점: [위도, 경도]
M_POINTS = {
    "A": [dms_to_decimal(35, 30, 0.8), dms_to_decimal(129, 23, 39.0)],
    "B": [dms_to_decimal(35, 29, 44.1), dms_to_decimal(129, 23, 41.2)],
    "C": [dms_to_decimal(35, 29, 33.7), dms_to_decimal(129, 23, 42.5)],
    "D": [dms_to_decimal(35, 29, 30.7), dms_to_decimal(129, 23, 43.0)],
    "E": [dms_to_decimal(35, 29, 17.0), dms_to_decimal(129, 23, 45.3)],
    "F": [dms_to_decimal(35, 29, 3.3), dms_to_decimal(129, 23, 47.7)],
    "G": [dms_to_decimal(35, 28, 49.6), dms_to_decimal(129, 23, 50.0)],
    "H": [dms_to_decimal(35, 28, 35.1), dms_to_decimal(129, 23, 52.5)],
    "I": [dms_to_decimal(35, 28, 35.1), dms_to_decimal(129, 24, 9.5)],
    "J": [dms_to_decimal(35, 28, 49.6), dms_to_decimal(129, 24, 9.5)],
    "K": [dms_to_decimal(35, 29, 3.3), dms_to_decimal(129, 24, 9.5)],
    "L": [dms_to_decimal(35, 29, 12.8), dms_to_decimal(129, 24, 9.4)],
    "M": [dms_to_decimal(35, 29, 17.0), dms_to_decimal(129, 24, 12.0)],
    "N": [dms_to_decimal(35, 29, 30.7), dms_to_decimal(129, 24, 20.6)],
    "O": [dms_to_decimal(35, 29, 35.4), dms_to_decimal(129, 24, 23.6)],
    "P": [dms_to_decimal(35, 29, 44.1), dms_to_decimal(129, 24, 16.6)],
    "Q": [dms_to_decimal(35, 29, 54.8), dms_to_decimal(129, 24, 7.9)],
    "R": [dms_to_decimal(35, 29, 44.1), dms_to_decimal(129, 23, 59.6)],
    "S": [dms_to_decimal(35, 29, 30.7), dms_to_decimal(129, 24, 1.3)],
}

M_ANCHORAGES = {
    "M1": {"code": "WAM-01", "capacity": "2천톤 이하", "points": ["A", "B", "P", "Q"]},
    "M2": {"code": "WAM-02", "capacity": "2천톤 이하", "points": ["B", "C", "D", "S", "R"]},
    "M3": {"code": "WAM-03", "capacity": "2천톤 이하", "points": ["N", "O", "P", "R", "S"]},
    "M4": {"code": "WAM-04", "capacity": "2천톤 이하", "points": ["D", "E", "M", "N"]},
    "M5": {"code": "WAM-05", "capacity": "2천톤 이하", "points": ["E", "F", "K", "L", "M"]},
    "M6": {"code": "WAM-06", "capacity": "2천톤 이하", "points": ["F", "G", "J", "K"]},
    "M7": {"code": "WAM-07", "capacity": "2천톤 이하", "points": ["G", "H", "I", "J"]},
}


# E묘박지: 직접 좌표 polygon
# E묘박지는 E1/E2/E3를 각각 따로 곡선 처리하지 않고,
# 전체 E묘박지 외곽을 하나의 큰 곡선 경계로 만든 뒤
# E1/E2/E3 분할선이 그 외곽선에 닿는 구조로 표현합니다.
#
# 목표 형태:
# - E1/E2/E3 오른쪽 외곽이 하나의 둥근 외곽선처럼 이어짐
# - 각 구역 사이의 경계선은 왼쪽 기준점에서 외곽 곡선까지 연결
# - 실제 항계선 곡선은 고시문상 곡선이므로, 여기서는 지도 표시용 근사 곡선입니다.

def bezier_curve(start, control1, control2, end, steps=80):
    """
    cubic Bezier curve
    start/control1/control2/end: [lat, lon]
    return: [[lat, lon], ...]
    """
    result = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t

        lat = (
            (mt ** 3) * start[0]
            + 3 * (mt ** 2) * t * control1[0]
            + 3 * mt * (t ** 2) * control2[0]
            + (t ** 3) * end[0]
        )

        lon = (
            (mt ** 3) * start[1]
            + 3 * (mt ** 2) * t * control1[1]
            + 3 * mt * (t ** 2) * control2[1]
            + (t ** 3) * end[1]
        )

        result.append([lat, lon])

    return result


def split_curve(curve, a_ratio, b_ratio):
    """
    전체 외곽 곡선에서 a_ratio~b_ratio 구간만 잘라냅니다.
    """
    n = len(curve)
    a = max(0, min(n - 1, int(round((n - 1) * a_ratio))))
    b = max(0, min(n - 1, int(round((n - 1) * b_ratio))))

    if a <= b:
        return curve[a:b + 1]
    return list(reversed(curve[b:a + 1]))


E1_P1 = [dms_to_decimal(35, 27, 59.0), dms_to_decimal(129, 24, 51.4)]
E1_P2 = [dms_to_decimal(35, 27, 59.0), dms_to_decimal(129, 25, 34.7)]
E1_P3 = [dms_to_decimal(35, 26, 46.7), dms_to_decimal(129, 27, 49.3)]
E1_P4 = [dms_to_decimal(35, 26, 13.6), dms_to_decimal(129, 24, 39.5)]
E1_P5 = [dms_to_decimal(35, 27, 43.4), dms_to_decimal(129, 24, 4.7)]

E2_P1 = E1_P4
E2_P2 = E1_P3
E2_P3 = [dms_to_decimal(35, 25, 29.8), dms_to_decimal(129, 28, 25.9)]
E2_P4 = [dms_to_decimal(35, 25, 12.7), dms_to_decimal(129, 25, 3.1)]

E3_P1 = E2_P4
E3_P2 = E2_P3
E3_P3 = [dms_to_decimal(35, 23, 2.5), dms_to_decimal(129, 27, 26.4)]
E3_P4 = [dms_to_decimal(35, 24, 11.0), dms_to_decimal(129, 25, 27.0)]


# 전체 E묘박지 오른쪽 외곽 곡선.
# 시작점은 E1 2번점, 끝점은 E3 3번점.
# control point는 네가 파란색으로 그린 큰 원형 외곽선을 기준으로 동쪽으로 충분히 밀어둔 값.
E_OUTER_CURVE = bezier_curve(
    E1_P2,
    [dms_to_decimal(35, 28, 10.0), dms_to_decimal(129, 28, 20.0)],
    [dms_to_decimal(35, 24, 35.0), dms_to_decimal(129, 30, 5.0)],
    E3_P3,
    steps=120,
)

# 전체 곡선에서 각 구역별로 나눠 쓸 구간.
# 비율은 실제 E1/E2/E3의 기준점 위치에 맞춰 조정.
E1_OUTER = split_curve(E_OUTER_CURVE, 0.00, 0.34)
E2_OUTER = split_curve(E_OUTER_CURVE, 0.34, 0.62)
E3_OUTER = split_curve(E_OUTER_CURVE, 0.62, 1.00)

# 각 구역의 외곽 곡선 끝점.
# 분할선은 왼쪽 기준점에서 이 끝점으로 연결되도록 구성.
E1_OUTER_START = E1_OUTER[0]
E1_OUTER_END = E1_OUTER[-1]
E2_OUTER_START = E2_OUTER[0]
E2_OUTER_END = E2_OUTER[-1]
E3_OUTER_START = E3_OUTER[0]
E3_OUTER_END = E3_OUTER[-1]


E_ANCHORAGES = {
    "E1": {
        "code": "WAE-01",
        "capacity": "1만톤 이하",
        "coords": [
            E1_P1,
            *E1_OUTER,
            E1_P4,
            E1_P5,
        ],
    },
    "E2": {
        "code": "WAE-02",
        "capacity": "3만톤 이하",
        "coords": [
            E2_P1,
            *E2_OUTER,
            E2_P4,
        ],
    },
    "E3": {
        "code": "WAE-03",
        "capacity": "2만톤 이상",
        "coords": [
            E3_P1,
            *E3_OUTER,
            E3_P4,
        ],
    },
}

# 부이 / 계류시설
# Leaflet L.circle은 meter radius 기준이라 확대/축소해도 실제 좌표와 반경에 고정됩니다.
MOORING_FACILITIES = {
    "W1": {
        "code": "WAW-01",
        "type": "계류시설",
        "capacity": "2만톤 이하",
        "lat": dms_to_decimal(35, 27, 17.0),
        "lon": dms_to_decimal(129, 23, 23.0),
        "radius_m": 400,
    },
    "T1": {
        "code": "WAT-01",
        "type": "계류시설",
        "capacity": "5천톤 이하",
        "lat": dms_to_decimal(35, 30, 37.3),
        "lon": dms_to_decimal(129, 27, 17.7),
        "radius_m": 300,
    },
    "T2": {
        "code": "WAT-02",
        "type": "계류시설",
        "capacity": "-",
        "lat": dms_to_decimal(35, 30, 57.0),
        "lon": dms_to_decimal(129, 27, 17.7),
        "radius_m": 300,
    },
    "T3": {
        "code": "WAT-03",
        "type": "계류시설",
        "capacity": "2천톤 이하",
        "lat": dms_to_decimal(35, 31, 40.2),
        "lon": dms_to_decimal(129, 27, 34.0),
        "radius_m": 250,
    },
        "SK_B#2": {
        "code": "SK_B#2",
        "type": "부이",
        "capacity": "-",
        "lat": 35.4388,
        "lon": 129.3934,
        "radius_m": 120,
    },

    "SK_B#3": {
        "code": "SK_B#3",
        "type": "부이",
        "capacity": "-",
        "lat": 35.4295,
        "lon": 129.3933,
        "radius_m": 120,
    },

    "S.OIL_B#1": {
        "code": "S.OIL_B#1",
        "type": "원유부이",
        "capacity": "-",
        "lat": 35.4071,
        "lon": 129.3954,
        "radius_m": 180,
    },

    "S.OIL_B#2": {
        "code": "S.OIL_B#2",
        "type": "원유부이",
        "capacity": "-",
        "lat": 35.3967,
        "lon": 129.3931,
        "radius_m": 180,
    },
}


@app.route("/")
def index():
    return "Ulsan Ship Map Server is running. Use /ship?name=TEST&lat=35.4919&lon=129.4004"


@app.route("/ship")
def ship_view():
    ship_name = request.args.get("name", "UNKNOWN")
    mmsi = request.args.get("mmsi", "-")
    lat = request.args.get("lat", "35.4500")
    lon = request.args.get("lon", "129.3800")
    sog = request.args.get("sog", "-")
    cog = request.args.get("cog", "0")
    status = request.args.get("status", "-")
    destination = request.args.get("destination", "-")
    departure = request.args.get("departure", "-")
    eta = request.args.get("eta", "-")

    try:
        length = float(request.args.get("length", "150"))
    except Exception:
        length = 150

    try:
        lat_float = float(lat)
        lon_float = float(lon)
    except Exception:
        lat_float = 35.45
        lon_float = 129.38

    try:
        cog_float = float(cog)
    except Exception:
        cog_float = 0

    m_points_json = json.dumps(M_POINTS, ensure_ascii=False)
    m_anchorages_json = json.dumps(M_ANCHORAGES, ensure_ascii=False)
    e_anchorages_json = json.dumps(E_ANCHORAGES, ensure_ascii=False)
    mooring_facilities_json = json.dumps(MOORING_FACILITIES, ensure_ascii=False)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{ship_name}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css">
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
            max-width: 330px;
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

        .area-label {{
            background: rgba(255,255,255,0.85);
            border: 1px solid #666;
            border-radius: 4px;
            color: #111827;
            font-weight: bold;
            padding: 2px 5px;
        }}

        .point-label {{
            background: rgba(255,255,255,0.9);
            border: 1px solid #999;
            border-radius: 3px;
            color: #374151;
            font-size: 11px;
            font-weight: bold;
            padding: 1px 3px;
        }}
    </style>
</head>

<body>
    <div class="info-box">
        <div class="title">🚢 {ship_name}</div>
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
        const lat = {lat_float};
        const lon = {lon_float};
        const cog = {cog_float};
        const shipLength = {length};

        const mPoints = {m_points_json};
        const mAnchorages = {m_anchorages_json};
        const eAnchorages = {e_anchorages_json};
        const mooringFacilities = {mooring_facilities_json};

        const map = L.map('map').setView([lat, lon], 13);

        const baseLayer = L.tileLayer(
            'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
            {{
                attribution: 'OpenStreetMap'
            }}
        ).addTo(map);

        const mLayer = L.layerGroup().addTo(map);
        const eLayer = L.layerGroup().addTo(map);
        const mooringLayer = L.layerGroup().addTo(map);
        const pointLayer = L.layerGroup();

        function centerOfCoords(coords) {{
            let latSum = 0;
            let lonSum = 0;
            coords.forEach(function(p) {{
                latSum += p[0];
                lonSum += p[1];
            }});
            return [latSum / coords.length, lonSum / coords.length];
        }}

        function addAnchoragePolygon(layer, name, code, capacity, coords, color, fillColor) {{
            const polygon = L.polygon(coords, {{
                color: color,
                weight: 2,
                fillColor: fillColor,
                fillOpacity: 0.18,
                dashArray: '6, 6'
            }}).addTo(layer);

            polygon.bindPopup(
                '<b>' + name + ' 정박구역</b><br>' +
                '시설코드: ' + code + '<br>' +
                '시설능력: ' + capacity
            );

            polygon.bindTooltip(name, {{
                permanent: true,
                direction: 'center',
                className: 'area-label'
            }});

            return polygon;
        }}


        function addMooringFacility(layer, name, item) {{
            const center = [item.lat, item.lon];

            const circle = L.circle(center, {{
                radius: item.radius_m,
                color: '#0f766e',
                weight: 2,
                fillColor: '#14b8a6',
                fillOpacity: 0.16,
                dashArray: '5, 5'
            }}).addTo(layer);

            circle.bindPopup(
                '<b>' + name + ' 계류시설</b><br>' +
                '시설코드: ' + item.code + '<br>' +
                '반경: ' + item.radius_m + 'm<br>' +
                '시설능력: ' + item.capacity
            );

            L.circleMarker(center, {{
                radius: 6,
                color: '#064e3b',
                fillColor: '#2dd4bf',
                fillOpacity: 1,
                weight: 2
            }}).addTo(layer).bindTooltip(name, {{
                permanent: true,
                direction: 'top',
                className: 'area-label'
            }});

            return circle;
        }}

        Object.keys(mAnchorages).forEach(function(name) {{
            const item = mAnchorages[name];
            const coords = item.points.map(function(pointName) {{
                return mPoints[pointName];
            }});

            addAnchoragePolygon(
                mLayer,
                name,
                item.code,
                item.capacity,
                coords,
                '#7c3aed',
                '#a855f7'
            );
        }});

        Object.keys(eAnchorages).forEach(function(name) {{
            const item = eAnchorages[name];

            addAnchoragePolygon(
                eLayer,
                name,
                item.code,
                item.capacity,
                item.coords,
                '#dc2626',
                '#f97316'
            );
        }});

        Object.keys(mooringFacilities).forEach(function(name) {{
            addMooringFacility(mooringLayer, name, mooringFacilities[name]);
        }});

        Object.keys(mPoints).forEach(function(key) {{
            const p = mPoints[key];
            L.circleMarker(p, {{
                radius: 3,
                color: '#111827',
                fillColor: '#ffffff',
                fillOpacity: 1,
                weight: 1
            }}).addTo(pointLayer).bindTooltip(key, {{
                permanent: true,
                direction: 'top',
                className: 'point-label'
            }});
        }});

        let markerSize = 20;
        if (shipLength >= 300) markerSize = 45;
        else if (shipLength >= 250) markerSize = 40;
        else if (shipLength >= 200) markerSize = 35;
        else if (shipLength >= 150) markerSize = 30;
        else if (shipLength >= 100) markerSize = 25;

        const shipIcon = L.divIcon({{
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
                    transform: rotate(${{cog}}deg);
                ">
                    ▲
                </div>
            `,
            iconSize: [markerSize, markerSize],
            iconAnchor: [markerSize / 2, markerSize / 2]
        }});

        const shipMarker = L.marker([lat, lon], {{
            icon: shipIcon
        }}).addTo(map)
          .bindPopup("<b>{ship_name}</b><br>MMSI: {mmsi}")
          .openPopup();

        const overlayMaps = {{
            "M묘박지": mLayer,
            "E묘박지": eLayer,
            "부이/계류시설": mooringLayer,
            "M 기준점 A~S": pointLayer
        }};

        L.control.layers(null, overlayMaps, {{
            collapsed: false
        }}).addTo(map);

        const bounds = L.latLngBounds([[lat, lon]]);
        mLayer.eachLayer(function(layer) {{
            if (layer.getBounds) bounds.extend(layer.getBounds());
        }});
        eLayer.eachLayer(function(layer) {{
            if (layer.getBounds) bounds.extend(layer.getBounds());
        }});
        mooringLayer.eachLayer(function(layer) {{
            if (layer.getBounds) bounds.extend(layer.getBounds());
            else if (layer.getLatLng) bounds.extend(layer.getLatLng());
        }});
        bounds.extend([lat, lon]);

        map.fitBounds(bounds, {{
            padding: [40, 40],
            maxZoom: 14
        }});
    </script>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
