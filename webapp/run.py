import uvicorn


if __name__ == "__main__":
    uvicorn.run("webapp.backend:app", host="127.0.0.1", port=8010, reload=False)
