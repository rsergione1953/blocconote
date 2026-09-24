import os
from struct import pack


def png_to_ico(png_path, ico_path):
    if not os.path.exists(png_path):
        print(f"Errore: Il file {png_path} non esiste!")
        return

    with open(png_path, "rb") as f:
        png_data = f.read()

    # Dimensione dell'immagine PNG
    width = 0  # 0 equivale a 256px
    height = 0

    # Intestazione file ICO
    header = pack("<HHH", 0, 1, 1)
    # Directory dell'immagine ICO
    directory = pack(
        "<BBBBHHII",
        width,
        height,
        0,
        0,
        1,
        32,
        len(png_data),
        6 + 16,  # Offset dei dati
    )

    with open(ico_path, "wb") as f:
        f.write(header)
        f.write(directory)
        f.write(png_data)

    print(f"Conversione completata! Creato: {ico_path}")


if __name__ == "__main__":
    png_input = os.path.join("assets", "logo.png")
    ico_output = os.path.join("assets", "icona.ico")
    png_to_ico(png_input, ico_output)
