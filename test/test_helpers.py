from app import application


def check_md_file(
    path,
    transcript_by,
    media,
    title=None,
    date=None,
    tags=None,
    category=None,
    speakers=None,
    local=False,
    chapters=None,
):
    is_correct = True
    if not path:
        return False
    with open(path, "r") as file:
        contents = file.read()
        file.close()

    data = contents.split("---\n")[1].strip().split("\n")
    body = contents.split("---\n")[2].strip()
    fields = {}

    for x in data:
        key = x.split(": ")[0]
        value = x.split(": ")[1]
        fields[key] = value

    detected_chapters = []

    for x in body.split("\n"):
        if x.startswith("##"):
            detected_chapters.append(x[3:].strip())

    assert fields["transcript_by"] == f"{transcript_by} via TBTBTC v{application.__version__}"

    if not local:
        assert fields["media"] == media
    assert fields["title"] == title

    if date:
        assert fields["date"] == date
    if tags:
        assert fields["tags"] == str(tags)
    if speakers:
        assert fields["speakers"] == str(speakers)
    if category:
        assert fields["categories"] == str(category)
    if chapters:
        assert detected_chapters == chapters
