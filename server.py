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
    assert audio_file.filename is not None

    try:
        tempdir = tempfile.mkdtemp(prefix="ai_osz_output_")
        input_tempfile = os.path.join(tempdir, audio_file.filename)
        with open(input_tempfile, "wb") as f:
            f.write(await audio_file.read())

        cmd = [
            "inference.py",
            "-cn",
            "inference_v30",
            "gamemode=0",
            f"audio_path={hydra_quote(input_tempfile)}",
            f"output_path={hydra_quote(tempdir)}",
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
        print(f"Generating AI map ({input_tempfile} -> {tempdir}/)")

        # Stream output line by line
        assert current_process.stdout is not None
        while True:
            line = await current_process.stdout.readline()
            if not line:
                break

            print(line.decode().strip())

        # find .osz file in output_tempdir
        osz_files = [f for f in os.listdir(tempdir) if f.endswith(".osz")]
        if not osz_files:
            raise FileNotFoundError(
                "No .osz file generated in the output directory."
            )
        output_osz_file = osz_files[0]

        return FileResponse(
            os.path.join(tempdir, output_osz_file),
            media_type="application/octet-stream",
            filename=audio_file.filename.rsplit(".", maxsplit=1)[0] + ".osz",
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
