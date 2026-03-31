
## Song Loops regions

## Sections Finder
- Try this implementation https://github.com/MWM-io/SpecTNT-pytorch
- Try this https://huggingface.co/osheroff/SongFormer

## Chords Finder


## Store reference/inferences in dedicated folders
- store inferences at analyzer/meta/{song}/infered/beats.{model_name}.json
- store references (source of truth) at analyzer/meta/{song}/reference/beats.json
  - references is human-validated data: it should be read-only; used to compare with the infered values.

## NiceToHave: 
- UI to select 

## (?) Self-Repo
- If so, create a small UI to:
  - select song
  - manage tasks queue
  - view files
  - view plots (plotly?)