package ru.mpgu.rasp.ui.nav

sealed class Dest(val route: String) {
    data object Onboarding : Dest("onboarding")
    data object Institutes : Dest("institutes")
    data class Groups(val instituteId: String) : Dest("groups/$instituteId") {
        companion object {
            const val ROUTE = "groups/{instituteId}"
            const val ARG = "instituteId"
        }
    }
    data class Week(val instituteId: String, val groupFile: String, val groupName: String) :
        Dest("week/$instituteId/$groupFile/${java.net.URLEncoder.encode(groupName, "UTF-8")}") {
        companion object {
            const val ROUTE = "week/{instituteId}/{groupFile}/{groupName}"
            const val ARG_INST = "instituteId"
            const val ARG_FILE = "groupFile"
            const val ARG_NAME = "groupName"
        }
    }
}
