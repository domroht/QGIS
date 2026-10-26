def classFactory(iface):
    from .ddm_qa_plugin import DdmQaPlugin

    return DdmQaPlugin(iface)