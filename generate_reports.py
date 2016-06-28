#!/usr/bin/env python

import argparse
import glob
import os
import shutil
from subprocess import Popen, PIPE
import sys

import jinja2
from jinja2 import Template
import yaml

import logging
import logging.config

from api import jenkins


with open("etc/logging.yaml") as f:
    d = yaml.load(f)
    d.setdefault("version", 1)
    logging.config.dictConfig(d)
logger = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate INDIGO-DataCloud SQA reports")
    parser.add_argument('template',
			metavar="LATEX_TEMPLATE",
			type=str,
			help="LaTeX template location.")
    parser.add_argument('specdir',
			metavar="YAML_SPECS_DIR",
			type=str,
			help="Directory with the YAML specs for each product.")
    parser.add_argument('--code-style',
                        metavar="YAML_FILE",
                        type=str,
                        help="Compile resulting LaTeX rendered file.")
    parser.add_argument('--output-dir',
			metavar="OUTPUT_DIR",
			type=str,
                        help="Directory to store the generated reports.")
    return parser.parse_args()


def load_yaml(fname):
    return yaml.load(open(fname, 'r'))


def load_jinja(fname):
    if os.path.isabs(fname):
        load_dir = os.path.dirname(fname)
    else:
        load_dir = os.path.dirname(os.path.abspath(fname))

    return jinja2.Environment(
            block_start_string = '\BLOCK{',
            block_end_string = '}',
            variable_start_string = '\VAR{',
            variable_end_string = '}',
            comment_start_string = '\#{',
            comment_end_string = '}',
            line_statement_prefix = '%%',
            line_comment_prefix = '%#',
            trim_blocks = True,
            autoescape = False,
            loader = jinja2.FileSystemLoader(load_dir)
    )


def add_jenkins_job(specs, job_type):
    if "jenkins_job" in specs[job_type].keys():
        if specs[job_type]["jenkins_job"]:
            specs[job_type]["jobs"] = {}
            for j in specs[job_type]["jenkins_job"]:
                specs[job_type]["jobs"][j] = {}
                specs[job_type]["jobs"][j]["job_url"] = jenkins.get_last_job_url(j)
                specs[job_type]["jobs"][j]["job_name"] = j
    elif "url_external" in specs[job_type].keys():
        if specs[job_type]["url_external"]:
            specs[job_type]["jobs"] = specs[job_type]["url_external"]
            logger.debug("External URL for %s found: %s"
                        % (job_type, specs[job_type]["jobs"]))



def main(fname, specdir, output=None, code_style=None):
    if os.path.isdir(specdir):
        spec_yaml_files = glob.glob(os.path.join(specdir, "*.yaml"))
    elif os.path.isfile(specdir):
        spec_yaml_files = [specdir]

    if not os.path.exists(output):
        os.makedirs(output)

    texfiles = []
    latex_jinja_env = load_jinja(fname)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if not code_style:
        code_style = load_yaml(os.path.join(current_dir,
                               "data/code_style.yaml"))
    if output:
        output = os.path.abspath(output)
    else:
        output = current_dir

    for f in spec_yaml_files:
        specs = load_yaml(f)
        logger.info("Parsing spec file '%s'" % f)

        # specs - code_style
        if specs["code_style"]["jenkins_job"]:
            logger.debug("Jenkins job/s for code style found.")
            specs["code_style"]["jobs"] = {}
            for j in specs["code_style"]["jenkins_job"]:
                specs["code_style"]["jobs"][j] = {}
                specs["code_style"]["jobs"][j]["job_url"] = jenkins.get_last_job_url(j)
                specs["code_style"]["jobs"][j]["job_name"] = j
        else:
            logger.debug("No Jenkins job found for code style.")
        if specs["code_style"]["standard"]:
            logger.debug("Code style standard/s adhered: %s"
                         % ','.join(specs["code_style"]["standard"]))
            try:
                for standard in specs["code_style"]["standard"]:
                    try:
                        specs["code_style"]["data"]
                    except KeyError:
                        specs["code_style"]["data"] = {}
                    specs["code_style"]["data"][standard] = code_style[standard]
            except KeyError as e:
                specs["code_style"]["data"] = {}
        else:
            logger.debug("No code_style standard/s defined.")

        # specs - unit_test
        if specs["unit_test"]["jenkins_job"]:
            specs["unit_test"]["job_url"] = jenkins.get_last_job_url(
                specs["unit_test"]["jenkins_job"])
            specs["unit_test"]["graph"] = jenkins.save_cobertura_graph(
                specs["unit_test"]["jenkins_job"],
                dest_dir=os.path.join(output, "figs"))
            specs["unit_test"]["data"] = jenkins.get_cobertura_data(
                specs["unit_test"]["jenkins_job"])
            logger.debug("Jenkins job for unit testing found: %s"
                         % specs["unit_test"]["job_url"])
        elif "url_external" in specs["unit_test"].keys():
            specs["unit_test"]["job_url"] = specs["unit_test"]["url_external"]
            logger.debug("External URL for unit testing found: %s"
                         % specs["unit_test"]["job_url"])
        else:
            logger.debug("No jenkins job defined in configuration.")

        # specs - func_int_test
        add_jenkins_job(specs, "func_int_test")
        if specs["func_int_test"]:
            logger.debug("Functional/integration tests defined.")
        else:
            logger.debug("No functional/integration definition found.")

        # specs - config_management
        specs["config_management"]["job_url"] = jenkins.get_last_job_url(
            specs["config_management"]["jenkins_job"])
        if specs["config_management"]["job_url"]:
            logger.debug("Configuration management job found: %s"
                         % specs["config_management"]["jenkins_job"])
        else:
            logger.debug("No Jenkins job for configuration management found.")

        # latex
        #FIXME(orviz) these values must be CLI arguments
        period="20-24 Jun 2016"
        weeks=12
        current_week=10
        logger.info("Reports being generated for period '%s' (week %s out of %s)" % (period, current_week, weeks))
        template = latex_jinja_env.get_template(os.path.basename(fname))
        r = template.render(
            product=specs,
            period=period,
            weeks=weeks,
            current_week=current_week,
        )

        texfile = os.path.basename(f).split('.')[0] + '.tex'
        texfiles.append(texfile)
        if output:
            open(os.path.join(output, texfile), 'w').write(r)
        else:
            print(r)

    if output:
        pdfdir = os.path.join(output, "pdf")
        if not os.path.exists(pdfdir):
            os.makedirs(pdfdir)
        for f in glob.glob(os.path.join(os.path.dirname(fname), "title_*.tex")):
            shutil.copy(f, output)
        for texfile in texfiles:
            f = os.path.join(output, texfile)
            logger.debug("Building LaTeX doc: %s" % f)
            cmd = ["pdflatex", "-output-directory=%s" % pdfdir, f]
            logger.debug("Running command: %s" % ' '.join(cmd))
            #p = Popen(["timeout", "60"]+cmd, stdout=PIPE, stderr=PIPE)
            logfile = '.'.join([texfile, ".log"])
            p = Popen(["timeout", "60"]+cmd, stdout=PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                open("logfile.log", 'w').write(stdout)
                logger.error("pdflatex command did not succeed! Check output at log: %s" % logfile)
                sys.exit(-1)
        logger.info("Report PDFs successfully generated in '%s'" % pdfdir)


if __name__ == "__main__":
    args = parse_args()
    main(args.template,
         args.specdir,
         code_style=args.code_style,
         output=args.output_dir)
