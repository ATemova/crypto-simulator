from fastapi.testclient import TestClient

from api import create_app
from blockchain.wallet import Wallet


def make_client():
    return TestClient(create_app(p2p_port=0, peers=[], difficulty=2))


def test_dashboard_and_static_assets_served():
    with make_client() as client:
        assert client.get("/").status_code == 200
        assert "Crypto Simulator" in client.get("/dashboard/").text
        assert client.get("/dashboard/styles.css").status_code == 200
        assert client.get("/dashboard/dashboard.js").status_code == 200


def test_mine_send_and_query():
    with make_client() as client:
        assert client.get("/chain").json()["length"] == 1
        block = client.post("/mine").json()["block"]
        assert block["index"] == 1
        assert client.get("/balance").json()["confirmed"] == 10

        recipient = Wallet().get_public_key_hex()
        res = client.post("/transactions", json={"recipient": recipient, "amount": 3})
        assert res.status_code == 201
        tx_id = res.json()["transaction"]["id"]
        assert client.get(f"/transactions/{tx_id}").json()["status"] == "pending"
        assert client.get("/balance").json()["available"] == 7

        client.post("/mine")
        assert client.get(f"/transactions/{tx_id}").json()["status"] == "confirmed"
        assert client.get("/balance", params={"address": recipient}).json()["confirmed"] == 3

        chain = client.get("/chain").json()
        assert chain["valid"] and chain["length"] == 3
        assert client.get("/peers").json() == {"peers": []}


def test_rejects_overspend_and_bad_input():
    with make_client() as client:
        recipient = Wallet().get_public_key_hex()
        res = client.post("/transactions", json={"recipient": recipient, "amount": 1})
        assert res.status_code == 400 and "Insufficient" in res.json()["detail"]
        assert client.post("/transactions", json={"recipient": recipient, "amount": -1}).status_code == 422
        assert client.post("/transactions", json={"recipient": "abc", "amount": 1}).status_code == 422
        assert client.post("/peers", json={"host": "127.0.0.1", "port": 1}).status_code == 400


def test_websocket_feed():
    with make_client() as client:
        with client.websocket_connect("/ws") as ws:
            first = ws.receive_json()
            assert first["state"]["height"] == 1
            assert len(first["blocks"]) == 1
            assert isinstance(first["peers"], list)
