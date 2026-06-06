from dotenv import load_dotenv                                                                                                                                                                                                                                         
load_dotenv() 

from fastapi import FastAPI
from mangum import Mangum
from app.routes import documents, analyze



app = FastAPI(title="Document Assistant API")

app.include_router(documents.router)
app.include_router(analyze.router)

# Esta línea es la magia: convierte FastAPI en Lambda handler
handler = Mangum(app, lifespan="off", api_gateway_base_path="/default")