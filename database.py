from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()
engine = create_engine('sqlite:///ocpp_cms.db', echo=True)
SessionLocal = sessionmaker(bind=engine)

class ChargingStation(Base):
    __tablename__ = 'charging_stations'
    
    id = Column(Integer, primary_key=True)
    station_id = Column(String, unique=True)
    status = Column(String)
    last_heartbeat = Column(DateTime)
    current_transaction = Column(String, nullable=True)
    vendor = Column(String)
    model = Column(String)
    current_power = Column(Float, default=0)  # Current power consumption in kW
    total_energy_consumed = Column(Float, default=0)  # Total energy consumed in kWh

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String, unique=True)
    station_id = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    meter_start = Column(Float)
    meter_stop = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    energy_consumed = Column(Float, default=0)  # Energy consumed in this transaction
    max_power = Column(Float, default=0)  # Maximum power during transaction

Base.metadata.create_all(engine)