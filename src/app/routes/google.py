from flask import Blueprint, jsonify, current_app
import requests

bp = Blueprint("google", __name__)

@bp.get("/reviews")
def google_reviews():
    s = current_app.config
    place, key = s['PLACE_ID'], s['GOOGLE_API_KEY']
    if not place or not key:
        return jsonify({"code": 200, "payload": []})
    url = ("https://maps.googleapis.com/maps/api/place/details/json"
           f"?place_id={place}&fields=reviews,rating,user_ratings_total,name&key={key}")
    try:
        data = requests.get(url, timeout=10).json()
        reviews = (data.get("result") or {}).get("reviews") or []
        return jsonify({"code": 200, "payload": reviews})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)})
