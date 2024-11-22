# ocpp_handler.py
import asyncio
import json
import logging
from datetime import datetime
import uuid
from database import SessionLocal, ChargingStation, Transaction

class OCPPHandler:
    def __init__(self):
        self.active_connections = {}
        self.charging_stations = {}
        
    async def handle_message(self, websocket, message):
        try:
            msg = json.loads(message)
            if len(msg) < 3:
                return
            
            message_type_id = msg[0]  # This is now an integer
            unique_id = msg[1]        # This is a string
            action = msg[2]           # This is a string
            payload = msg[3] if len(msg) > 3 else {}  # This is a dictionary
            
            if message_type_id == 2:  # Call
                response = await self.handle_call(websocket, action, payload)
                await websocket.send_text(json.dumps([3, unique_id, response]))
                
        except Exception as e:
            logging.error(f"Error handling message: {e}")
            logging.error(f"Message received: {message}")




            
    async def handle_call(self, websocket, action, payload):
        db = SessionLocal()
        try:
            if action == "BootNotification":
                # Get the charge point ID from the payload
                charge_point_id = payload.get("chargePointId")
                vendor = payload.get("chargePointVendor")
                model = payload.get("chargePointModel")
                
                logging.info(f"Processing BootNotification for station {charge_point_id}")
                logging.info(f"Payload: {payload}")
                
                # Check if station exists
                station = db.query(ChargingStation).filter_by(station_id=charge_point_id).first()
                
                if station:
                    # Update existing station
                    station.vendor = vendor
                    station.model = model
                    station.last_heartbeat = datetime.utcnow()
                    station.status = "Available"
                else:
                    # Create new station
                    station = ChargingStation(
                        station_id=charge_point_id,
                        vendor=vendor,
                        model=model,
                        status="Available",
                        last_heartbeat=datetime.utcnow(),
                        current_power=0.0,
                        total_energy_consumed=0.0
                    )
                    db.add(station)
                
                try:
                    db.commit()
                    logging.info(f"Successfully processed BootNotification for station {charge_point_id}")
                except Exception as e:
                    db.rollback()
                    logging.error(f"Database error during BootNotification: {e}")
                    raise
                
                return {
                    "status": "Accepted",
                    "currentTime": datetime.utcnow().isoformat(),
                    "interval": 300
                }
                
            elif action == "StartTransaction":
                station_id = payload.get("chargePointId")
                transaction_id = str(payload.get("transactionId"))
                meter_start = float(payload.get("meterStart", 0))
                
                transaction = Transaction(
                    transaction_id=transaction_id,
                    station_id=station_id,
                    start_time=datetime.utcnow(),
                    meter_start=meter_start,
                    is_active=True,
                    energy_consumed=0.0,
                    max_power=0.0
                )
                
                db.add(transaction)
                station = db.query(ChargingStation).filter_by(station_id=station_id).first()
                if station:
                    station.status = "Charging"
                    station.current_transaction = transaction_id
                db.commit()
                
                return {
                    "transactionId": transaction_id,
                    "idTagInfo": {"status": "Accepted"}
                }
                
            elif action == "Meter":
                station_id = payload.get("chargePointId")
                current_power = float(payload.get("power", 0))
                
                station = db.query(ChargingStation).filter_by(station_id=station_id).first()
                if station and station.current_transaction:
                    station.current_power = current_power
                    
                    transaction = db.query(Transaction).filter_by(
                        transaction_id=station.current_transaction,
                        is_active=True
                    ).first()
                    
                    if transaction:
                        energy_increment = (current_power * 5) / 3600
                        transaction.energy_consumed += energy_increment
                        transaction.max_power = max(transaction.max_power, current_power)
                        station.total_energy_consumed += energy_increment
                    
                    db.commit()
                
                return {"status": "Accepted"}
                
            elif action == "StopTransaction":
                station_id = payload.get("chargePointId")
                transaction_id = str(payload.get("transactionId"))
                
                transaction = db.query(Transaction).filter_by(
                    transaction_id=transaction_id,
                    is_active=True
                ).first()
                
                if transaction:
                    transaction.end_time = datetime.utcnow()
                    transaction.is_active = False
                    
                    station = db.query(ChargingStation).filter_by(station_id=station_id).first()
                    if station:
                        station.status = "Available"
                        station.current_transaction = None
                        station.current_power = 0
                    
                    db.commit()
                
                return {"idTagInfo": {"status": "Accepted"}}


            elif action == "StopTransactionFromCMS":
                    transaction_id = payload.get("transactionId")
                    transaction = db.query(Transaction).filter_by(transaction_id=transaction_id).first()
                    
                    if transaction:
                        transaction.end_time = datetime.utcnow()
                        transaction.is_active = False
                        
                        station = db.query(ChargingStation).filter_by(station_id=transaction.station_id).first()
                        if station:
                            station.status = "Available"
                            station.current_transaction = None
                            station.current_power = 0
                        
                        db.commit()
                        
                    return {"status": "Accepted", "message": "Transaction stopped"}
                
        except Exception as e:
            logging.error(f"Error in handle_call: {e}")
            db.rollback()
            raise
        finally:
            db.close()
            
        return {"status": "Accepted"}