import subprocess
import sys
import tempfile
from fastapi import FastAPI, File, Response, UploadFile
from fastapi.responses import FileResponse

app = FastAPI()


def hydra_quote(value):
    """Quotes a value for Hydra (single quotes, escapes internal)."""
    value_str = str(value)
    # Escape internal single quotes: ' -> '\''
    escaped_value = value_str.replace("'", r"\'")
    return f"'{escaped_value}'"


@app.post("/ai-maps")
async def generate_map(
    difficulty: float,
    audio_file: UploadFile = File(...),
):
    try:
        assert audio_file.filename is not None
        file_extension = audio_file.filename.rsplit(".", maxsplit=1)[-1]
        with (
            tempfile.NamedTemporaryFile(suffix=f".{file_extension}") as input_tempfile,
            tempfile.NamedTemporaryFile(suffix=".osz", delete=False) as output_tempfile,
        ):
            # Save the uploaded audio file to a temporary file
            input_tempfile.write(await audio_file.read())

            cmd = [
                sys.executable,
                "inference.py",
                "-cn",
                "inference_v30",
                "gamemode=0",
                f"audio_path={hydra_quote(input_tempfile.name)}",
                f"output_path={hydra_quote(output_tempfile.name)}",
                f"difficulty={difficulty}",
                "export_osz=true",
                "super_timing=false",
                "hitsounded=false",
                "add_to_beatmap=false",
            ]
            current_process = subprocess.Popen(
                cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
            )
            print(
                f"Generating AI map ({input_tempfile.name} -> {output_tempfile.name})"
            )
            stdout, _ = current_process.communicate()
            print(stdout)

            return FileResponse(output_tempfile.name)

    except Exception as e:
        return Response({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", reload=True)
