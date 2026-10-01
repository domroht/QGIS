from pathlib import Path
import subprocess

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterFileDestination,
)


class RunQaAlgorithm(QgsProcessingAlgorithm):

    DYBDE = "DYBDE"
    KILDE = "KILDE"
    AAR = "AAR"
    OUTPUT_DIR = "OUTPUT_DIR"
    PERCENTILE = "PERCENTILE"
    CONNECTIVITY = "CONNECTIVITY"
    LOCAL_RANGE = "LOCAL_RANGE"
    PL_VARIATION = "PL_VARIATION"
    PL_VARIATION_AREAS = "PL_VARIATION_AREAS"
    QA_RESULTS = "QA_RESULTS"
    REPORT_HTML = "REPORT_HTML"

    def name(self):
        return "run_qa"

    def displayName(self):
        return "Run DDM QA"

    def group(self):
        return "DDM QA"

    def groupId(self):
        return "ddmqa"

    def createInstance(self):
        return RunQaAlgorithm()

    # Definer input/output
    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFile(
                self.DYBDE,
                "Dybde raster",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="GeoTIFF (*.tif *.tiff)",
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.KILDE,
                "Kilde raster",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="GeoTIFF (*.tif *.tiff)",
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.AAR,
                "År raster",
                behavior=QgsProcessingParameterFile.File,
                fileFilter="GeoTIFF (*.tif *.tiff)",
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.PERCENTILE,
                "Percentile limit",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=95,
                minValue=1,
                maxValue=99,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.CONNECTIVITY,
                "Area connectivity",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=8,
                minValue=4,
                maxValue=8,
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_DIR,
                "Output folder",
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.LOCAL_RANGE,
                "Local range",
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.PL_VARIATION,
                "PL variation",
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.PL_VARIATION_AREAS,
                "PL variation areas",
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.QA_RESULTS,
                "QA results JSON",
                fileFilter="JSON files (*.json)",
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.REPORT_HTML,
                "QA report HTML",
                fileFilter="HTML files (*.html *.htm)",
            )
        )

    # Bliver kaldt når man trykker på run i QGIS
    def processAlgorithm(self, parameters, context, feedback):

        dybde = Path(
            self.parameterAsFile(
                parameters,
                self.DYBDE,
                context,
            )
        )

        kilde = Path(
            self.parameterAsFile(
                parameters,
                self.KILDE,
                context,
            )
        )

        aar = Path(
            self.parameterAsFile(
                parameters,
                self.AAR,
                context,
            )
        )

        output_dir = Path(
            self.parameterAsString(
                parameters,
                self.OUTPUT_DIR,
                context,
            )
        )

        percentile = self.parameterAsInt(
            parameters,
            self.PERCENTILE,
            context,
        )

        connectivity = self.parameterAsInt(
            parameters,
            self.CONNECTIVITY,
            context,
        )

        plugin_dir = Path(__file__).resolve().parents[1]
        project_dir = plugin_dir.parent

        """
        qa_executable = project_dir / "dist" / "ddm_qa"

        if not qa_executable.exists():
            raise QgsProcessingException(
                f"DDM QA executable not found: {qa_executable}"
            )


        erstat nedenstående med dette senere (efter pyinstaller build)
        """

        python_executable = project_dir / ".venv" / "bin" / "python"
        qa_script = project_dir / "ddm_qa_cli.py"

        if not python_executable.exists():
            raise QgsProcessingException(
                f"Python environment not found: {python_executable}"
            )

        if not qa_script.exists():
            raise QgsProcessingException(
                f"QA script not found: {qa_script}"
            )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        local_range = Path(self.parameterAsOutputLayer(parameters, self.LOCAL_RANGE, context))

        pl_variation = Path(self.parameterAsOutputLayer(parameters, self.PL_VARIATION, context))

        pl_variation_areas = Path(self.parameterAsOutputLayer(parameters, self.PL_VARIATION_AREAS, context))

        result_json = Path(self.parameterAsFileOutput(parameters, self.QA_RESULTS, context))

        report_path = self.parameterAsFileOutput(parameters, self.REPORT_HTML, context)

        feedback.pushInfo(f"Local range output: {local_range}")

        feedback.pushInfo(f"PL variation output: {pl_variation}")

        feedback.pushInfo(f"PL variation areas output: {pl_variation_areas}")

        feedback.pushInfo(f"QA results output: {result_json}")

        feedback.pushInfo(f"QA report output: {report_path}")

        # fjern python_executable og qa_script og erstat med str(qa_executable),
        command = [
            str(python_executable),
            str(qa_script),
            "--dybde",
            str(dybde),
            "--kilde",
            str(kilde),
            "--aar",
            str(aar),
            "--local-range",
            str(local_range),
            "--pl-variation",
            str(pl_variation),
            "--pl-variation-areas",
            str(pl_variation_areas),
            "--percentile-limit",
            str(percentile),
            "--pl-area-connect",
            str(connectivity),
            "--result-json",
            str(result_json),
            "--report-html",
            str(report_path),
        ]

        feedback.pushInfo("Starting DDM QA engine...")

        """
        feedback.pushInfo(f"Executable: {qa_executable}")

        erstat de to nedenstående med feedback.pushinfo senerer
        """

        feedback.pushInfo(f"Python: {python_executable}")

        feedback.pushInfo(f"Script: {qa_script}")

        feedback.pushInfo("Running QA...")

        # start comando output og fejl skal ske i samme log
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # print process i QGIS
        for line in process.stdout:
            line = line.rstrip()

            if line:
                feedback.pushInfo(line)

            if feedback.isCanceled():
                process.terminate()
                process.wait()
                raise QgsProcessingException(
                    "DDM QA was canceled"
                )

        return_code = process.wait()

        if return_code != 0:
            raise QgsProcessingException(
                f"DDM QA failed with exit code {return_code}"
            )

        feedback.pushInfo("DDM QA completed successfully")

        return {
            self.LOCAL_RANGE: str(local_range),
            self.PL_VARIATION: str(pl_variation),
            self.PL_VARIATION_AREAS: str(pl_variation_areas),
            self.QA_RESULTS: str(result_json),
            self.REPORT_HTML: str(report_path),
        }