from fastapi import FastAPI
from chainlit.utils import mount_chainlit

app = FastAPI()


@app.get("/")
def read_main():
    return {"message": "Hello World from main app"}


mount_chainlit(app=app, target="app/cl_app.py", path="/chainlit")

# Note: This should be for development purposes only. In production, this will use Gunicorn with Uvicorn workers.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
