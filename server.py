from pydantic import BaseModel
import inference


from fastapi import FastAPI

app = FastAPI()


class InferenceRequest(BaseModel):
    audio_path: str
    output_path: str
    gamemode: int
    difficulty: float


@app.post("/ai-maps")
async def generate_map(request: InferenceRequest):
    """
    Endpoint to generate a map using the provided request data.
    """
    try:
        response = await inference.main(
            inference.InferenceConfig(
                audio_path=request.audio_path,
                output_path=request.output_path,
                gamemode=request.gamemode,
                difficulty=request.difficulty,
                export_osz=True,
            ),
        )
        with open(response[2], "rb") as f:
            osz_content = f.read()
        return osz_content
    except Exception as e:
        return {"error": str(e)}
