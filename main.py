from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.websockets import WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import uvicorn
import logging
from database import SessionLocal, ChargingStation, Transaction
from ocpp_handler import OCPPHandler

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

ocpp_handler = OCPPHandler()






# Store for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.error(f"Error broadcasting message: {e}")

                


                

manager = ConnectionManager()

# Add broadcast method to OCPPHandler
ocpp_handler.ws_manager = manager








@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)






@app.get("/")
async def home(request: Request):
    db = SessionLocal()
    stations = db.query(ChargingStation).all()
    transactions = db.query(Transaction).filter_by(is_active=True).all()
    db.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "stations": stations, "transactions": transactions}
    )









@app.post("/stop-transaction/{transaction_id}")
async def stop_transaction(transaction_id: str):
    db = SessionLocal()
    try:
        # Add logging to help debug
        logging.info(f"Attempting to stop transaction: {transaction_id}")
        
        transaction = db.query(Transaction).filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            logging.warning(f"Transaction not found: {transaction_id}")
            return JSONResponse(
                status_code=404, 
                content={"status": "error", "message": "Transaction not found"}
            )
        
        if not transaction.is_active:
            logging.warning(f"Transaction already stopped: {transaction_id}")
            return JSONResponse(
                status_code=400, 
                content={"status": "error", "message": "Transaction is already stopped"}
            )
        
        # Find the corresponding charging station
        station = db.query(ChargingStation).filter_by(station_id=transaction.station_id).first()
        
        if not station:
            logging.warning(f"Station not found for transaction: {transaction_id}")
            return JSONResponse(
                status_code=404, 
                content={"status": "error", "message": "Charging station not found"}
            )
        
        # Simulate OCPP stop transaction message
        # Note: This might need to be a synchronous call if async is causing issues
        # You might need to modify OCPPHandler to handle this synchronously
        result = await ocpp_handler.handle_call(None, "StopTransactionFromCMS", {
            "transactionId": transaction_id,
            "chargePointId": station.station_id
        })
        
        logging.info(f"Transaction stopped successfully: {transaction_id}")
        return JSONResponse({
            "status": "success", 
            "message": "Transaction stopped",
            "result": result
        })
    
    except Exception as e:
        logging.error(f"Error stopping transaction {transaction_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "message": str(e)}
        )
    finally:
        db.close()













@app.websocket("/ocpp/{station_id}")
async def websocket_endpoint(websocket: WebSocket, station_id: str):
    await websocket.accept()
    ocpp_handler.active_connections[websocket] = station_id
    
    try:
        while True:
            message = await websocket.receive_text()
            await ocpp_handler.handle_message(websocket, message)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        del ocpp_handler.active_connections[websocket]







if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)








# Rest of the code remains the same