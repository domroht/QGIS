from qgis.core import QgsProcessingProvider
from .run_ddm_qa import RunQaAlgorithm

class Provider(QgsProcessingProvider):

    def loadAlgorithms(self):
        self.addAlgorithm(RunQaAlgorithm())

    def id(self) -> str:
        return "ddmqa"

    def name(self) -> str:
        return self.tr("DDM QA")

    def longName(self) -> str:
        return self.tr("DDM QA")