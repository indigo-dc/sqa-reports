# INDIGO-DataCloud SQA reports

Tool to generate SQA reports for INDIGO-DataCloud products.

## Description

The script collects data from YAMLs (statically gathered) and service APIs (dynamic retrieval) of tools used in the project. This data is then used to create the PDF reports using a [TEX template](templates/report.tex).

Each product has its corresponding YAML file, stored in the [specs](specs) directory.

There is an additional [data](data) directory, where extended information that will appear in the reports is stored. An example of this is the [code style standards](data/code_style.yaml).

## How to run it

### Through Docker

A [Dockerfile](docker/Dockerfile) has been provided to facilitate the setup of the adequate environment for the report generation.

```{r, engine='bash', count_lines}
docker pull indigodatacloud/sqa-reports
docker run -it indigodatacloud/sqa-reports bash

(container)$ python generate_reports.py templates/report.tex specs/ --output-dir=/srv/sqa-reports/build
```

TEX and PDF reports should be available in /srv/sqa-reports/build.

### Through Python's virtualenv.

*Note that in this case additional development libraries need to be available in the OS before installing the requirements.txt*

```{r, engine='bash', count_lines}
virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_reports.py templates/report.tex specs/ --output-dir=/srv/sqa-reports/build
```

TEX and PDF reports should be available in /srv/sqa-reports/build.
