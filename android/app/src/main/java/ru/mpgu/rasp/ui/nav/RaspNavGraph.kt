package ru.mpgu.rasp.ui.nav

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import ru.mpgu.rasp.ui.groups.GroupsScreen
import ru.mpgu.rasp.ui.institutes.InstitutesScreen
import ru.mpgu.rasp.ui.onboarding.OnboardingScreen
import ru.mpgu.rasp.ui.week.WeekScreen
import java.net.URLDecoder

@Composable
fun RaspNavGraph(startDestination: String) {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = startDestination) {
        composable(Dest.Onboarding.route) {
            OnboardingScreen(
                onPicked = { inst, file, name ->
                    nav.navigate(Dest.Week(inst, file, name).route) {
                        popUpTo(Dest.Onboarding.route) { inclusive = true }
                    }
                }
            )
        }
        composable(Dest.Institutes.route) {
            InstitutesScreen(onSelect = { id -> nav.navigate(Dest.Groups(id).route) })
        }
        composable(
            Dest.Groups.ROUTE,
            arguments = listOf(navArgument(Dest.Groups.ARG) { type = NavType.StringType }),
        ) { entry ->
            val id = entry.arguments!!.getString(Dest.Groups.ARG)!!
            GroupsScreen(
                instituteId = id,
                onSelect = { file, name -> nav.navigate(Dest.Week(id, file, name).route) },
            )
        }
        composable(
            Dest.Week.ROUTE,
            arguments = listOf(
                navArgument(Dest.Week.ARG_INST) { type = NavType.StringType },
                navArgument(Dest.Week.ARG_FILE) { type = NavType.StringType },
                navArgument(Dest.Week.ARG_NAME) { type = NavType.StringType },
            ),
        ) { entry ->
            val id = entry.arguments!!.getString(Dest.Week.ARG_INST)!!
            val file = entry.arguments!!.getString(Dest.Week.ARG_FILE)!!
            val name = URLDecoder.decode(entry.arguments!!.getString(Dest.Week.ARG_NAME)!!, "UTF-8")
            WeekScreen(instituteId = id, groupFile = file, groupName = name)
        }
    }
}
