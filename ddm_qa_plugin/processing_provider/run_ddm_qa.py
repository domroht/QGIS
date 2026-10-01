from pathlib import Path
import math
import subprocess

from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterFileDestination,
    QgsRasterLayer,
    QgsSingleBandPseudoColorRenderer,
    QgsColorRampShader,
    QgsRasterShader,
    QgsPalettedRasterRenderer,
    QgsProject,
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


    # helper til at finde værdierne for de enklte rastere
    def _scan_raster_values(self, layer, feedback, ignore_values=None):

        if ignore_values is None:
            ignore_values = set()

        provider = layer.dataProvider()

        width = layer.width()
        height = layer.height()

        if width <= 0 or height <= 0:
            raise QgsProcessingException("Raster has invalid dimensions.")

        block = provider.block(
            1,
            layer.extent(),
            width,
            height,
        )

        if block is None:
            raise QgsProcessingException("Could not read raster block.")

        min_value = None
        max_value = None
        unique_values = set()

        for row in range(height):

            if feedback.isCanceled():
                raise QgsProcessingException("DDM QA was canceled")

            for column in range(width):

                if block.isNoData(row, column):
                    continue

                value = block.value(row, column)

                if value in ignore_values:
                    continue

                if isinstance(value, float) and math.isnan(value):
                    continue

                if min_value is None or value < min_value:
                    min_value = value

                if max_value is None or value > max_value:
                    max_value = value

                unique_values.add(value)

        return min_value, max_value, sorted(unique_values)


    #=====================================#
    #==       STYLE HELPER FUNCS        ==#
    #=====================================#

    def _style_local_range(self, layer, feedback):

        min_value, max_value, _ = self._scan_raster_values(
            layer,
            feedback,
            ignore_values={
                255,
                -9999,
            },
        )

        if min_value is None or max_value is None:
            raise QgsProcessingException("Local range contains no valid data.")

        color_ramp = QgsColorRampShader()

        color_ramp.setColorRampType(
            QgsColorRampShader.Interpolated
        )

        if min_value == max_value:

            color_ramp.setColorRampItemList([
                QgsColorRampShader.ColorRampItem(
                    min_value,
                    QColor("#6baed6"),
                    str(min_value),
                )
            ])

        else:

            color_ramp.setColorRampItemList([
                QgsColorRampShader.ColorRampItem(
                    min_value,
                    QColor("#d9f0ff"),
                    str(min_value),
                ),
                QgsColorRampShader.ColorRampItem(
                    max_value,
                    QColor("#08306b"),
                    str(max_value),
                ),
            ])

        # QgsSingleBandPseudoColorRenderer forventer en QgsRasterShader og ikke direkte en QgsColorRampShader
        shader = QgsRasterShader()

        shader.setRasterShaderFunction(color_ramp)

        renderer = QgsSingleBandPseudoColorRenderer(
            layer.dataProvider(),
            1,
            shader,
        )

        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def _style_pl_variation(self, layer, feedback):

        classes = [
            QgsPalettedRasterRenderer.Class(
                0,
                QColor(0, 0, 0, 0),
                "Not above percentile",
            ),
            QgsPalettedRasterRenderer.Class(
                1,
                QColor(217, 217, 217, 51),
                "Above percentile",
            ),
        ]

        renderer = QgsPalettedRasterRenderer(
            layer.dataProvider(),
            1,
            classes,
        )

        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def _get_area_color(self, index):

        golden_angle = 0.618033988749895

        hue = (index * golden_angle) % 1.0

        saturation = 0.70
        value = 0.95

        return QColor.fromHsvF(
            hue,
            saturation,
            value,
            1.0,
        )

    def _style_pl_variation_areas(self, layer, feedback):

        _, _, unique_values = self._scan_raster_values(
            layer,
            feedback,
            ignore_values={0},
        )

        if not unique_values:
            feedback.pushInfo("PL variation areas contains no areas.")
            return

        classes = []

        for index, value in enumerate(unique_values):

            if float(value).is_integer():
                area_value = int(value)
                label = f"Area {area_value}"
            else:
                area_value = value
                label = f"Area {value}"

            color = self._get_area_color(index)

            classes.append(
                QgsPalettedRasterRenderer.Class(
                    area_value,
                    color,
                    label,
                )
            )

        renderer = QgsPalettedRasterRenderer(
            layer.dataProvider(),
            1,
            classes,
        )

        layer.setRenderer(renderer)
        layer.triggerRepaint()


    #=====================================#
    #==             KØR QA              ==#
    #=====================================#

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
            raise QgsProcessingException(f"Python environment not found: {python_executable}")

        if not qa_script.exists():
            raise QgsProcessingException(f"QA script not found: {qa_script}")

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        local_range = Path(
            self.parameterAsOutputLayer(
                parameters,
                self.LOCAL_RANGE,
                context,
            )
        )

        pl_variation = Path(
            self.parameterAsOutputLayer(
                parameters,
                self.PL_VARIATION,
                context,
            )
        )

        pl_variation_areas = Path(
            self.parameterAsOutputLayer(
                parameters,
                self.PL_VARIATION_AREAS,
                context,
            )
        )

        result_json = Path(
            self.parameterAsFileOutput(
                parameters,
                self.QA_RESULTS,
                context,
            )
        )

        report_path = self.parameterAsFileOutput(
            parameters,
            self.REPORT_HTML,
            context,
        )

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
                raise QgsProcessingException("DDM QA was canceled")

        return_code = process.wait()

        if return_code != 0:
            raise QgsProcessingException(
                f"DDM QA failed with exit code {return_code}"
            )

        feedback.pushInfo("DDM QA completed successfully")


        #=====================================#
        #==       LOAD OUTPUT RASTERS       ==#
        #=====================================#

        feedback.pushInfo("Loading QA rasters...")

        local_range_layer = QgsRasterLayer(
            str(local_range),
            "Local range",
            "gdal",
        )

        pl_variation_layer = QgsRasterLayer(
            str(pl_variation),
            "PL variation",
            "gdal",
        )

        pl_variation_areas_layer = QgsRasterLayer(
            str(pl_variation_areas),
            "PL variation areas",
            "gdal",
        )

        if not local_range_layer.isValid():
            raise QgsProcessingException(
                f"Could not load local range raster: "
                f"{local_range}"
            )

        if not pl_variation_layer.isValid():
            raise QgsProcessingException(
                f"Could not load PL variation raster: "
                f"{pl_variation}"
            )

        if not pl_variation_areas_layer.isValid():
            raise QgsProcessingException(
                f"Could not load PL variation areas raster: "
                f"{pl_variation_areas}"
            )

        #=====================================#
        #==       TILFØJ RASTER STYLES      ==#
        #=====================================#

        feedback.pushInfo("Styling output rasters")

        self._style_local_range(local_range_layer, feedback)

        self._style_pl_variation(pl_variation_layer, feedback)

        self._style_pl_variation_areas(pl_variation_areas_layer, feedback)


        QgsProject.instance().addMapLayer(local_range_layer)

        QgsProject.instance().addMapLayer(pl_variation_layer)

        QgsProject.instance().addMapLayer(pl_variation_areas_layer)

        feedback.pushInfo("Styled QA rasters added to QGIS.")

        return {
            self.LOCAL_RANGE: str(local_range),
            self.PL_VARIATION: str(pl_variation),
            self.PL_VARIATION_AREAS: str(pl_variation_areas),
            self.QA_RESULTS: str(result_json),
            self.REPORT_HTML: str(report_path),
        }