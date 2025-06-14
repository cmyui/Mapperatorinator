from asyncio import subprocess
import os
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


@app.post("/ai-osz-files")
async def generate_map(
    difficulty: float,
    audio_file: UploadFile = File(...),
):
    output_tempdir: str | None = None
    try:
        output_tempdir = tempfile.mkdtemp(prefix="ai_osz_output_")
        assert audio_file.filename is not None
        file_extension = audio_file.filename.rsplit(".", maxsplit=1)[-1]
        with tempfile.NamedTemporaryFile(suffix=f".{file_extension}") as input_tempfile:

            # Save the uploaded audio file to a temporary file
            input_tempfile.write(await audio_file.read())

            cmd = [
                "inference.py",
                "-cn",
                "inference_v30",
                "gamemode=0",
                f"audio_path={hydra_quote(input_tempfile.name)}",
                f"output_path={hydra_quote(output_tempdir)}",
                f"difficulty={difficulty}",
                "export_osz=true",
                "super_timing=false",
                "hitsounded=false",
                "add_to_beatmap=false",
            ]
            current_process = await subprocess.create_subprocess_exec(
                sys.executable,
                *cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            print(f"Generating AI map ({input_tempfile.name} -> {output_tempdir})")

            # Stream output line by line
            assert current_process.stdout is not None
            while True:
                line = await current_process.stdout.readline()
                if not line:
                    break

                print(line.decode().strip())

            # find .osz file in output_tempdir
            osz_files = [f for f in os.listdir(output_tempdir) if f.endswith(".osz")]
            if not osz_files:
                raise FileNotFoundError(
                    "No .osz file generated in the output directory."
                )
            output_osz_file = osz_files[0]

            return FileResponse(
                os.path.join(output_tempdir, output_osz_file),
                media_type="application/octet-stream",
                filename=output_osz_file,
            )

    except Exception as e:
        return Response({"error": str(e)}, status_code=500)
    # TODO: schedule for deletion later or something; this thing race cond's
    # finally:
    #     if output_tempdir and os.path.exists(output_tempdir):
    #         try:
    #             # Remove the temporary directory and its contents
    #             for root, dirs, files in os.walk(output_tempdir, topdown=False):
    #                 for name in files:
    #                     os.remove(os.path.join(root, name))
    #                 for name in dirs:
    #                     os.rmdir(os.path.join(root, name))
    #             os.rmdir(output_tempdir)
    #         except Exception as cleanup_error:
    #             print(f"Error cleaning up temporary directory: {cleanup_error}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", reload=True)
