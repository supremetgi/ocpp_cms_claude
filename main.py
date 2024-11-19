from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
import uvicorn
from database import SessionLocal, ChargingStation, Transaction
from ocpp_handler import OCPPHandler

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

ocpp_handler = OCPPHandler()

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
        transaction = db.query(Transaction).filter_by(transaction_id=transaction_id).first()
        
        if not transaction or not transaction.is_active:
            raise HTTPException(status_code=404, detail="Active transaction not found")
        
        # Find the corresponding charging station
        station = db.query(ChargingStation).filter_by(station_id=transaction.station_id).first()
        
        if not station:
            raise HTTPException(status_code=404, detail="Charging station not found")
        
        # Simulate OCPP stop transaction message
        await ocpp_handler.handle_call(None, "StopTransactionFromCMS", {
            "transactionId": transaction_id,
            "chargePointId": station.station_id
        })
        
        return JSONResponse({"status": "success", "message": "Transaction stopped"})
    
    except Exception as e:
        logging.error(f"Error stopping transaction: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        db.close()








# @app.post("/stop-transaction/{transaction_id}")
# async def stop_transaction(transaction_id: str):
#     db = SessionLocal()
#     try:
#         transaction = db.query(Transaction).filter_by(transaction_id=transaction_id).first()
        
#         if not transaction or not transaction.is_active:
#             raise HTTPException(status_code=404, detail="Active transaction not found")
        
#         # Simulate OCPP stop transaction message
#         stop_payload = {
#             "transactionId": transaction_id
#         }
        
#         await ocpp_handler.handle_call(None, "StopTransactionFromCMS", {"transactionId": transaction_id})
        
#         return JSONResponse({"status": "success", "message": "Transaction stopped"})
    
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
#     finally:
#         db.close()




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