package ru.mpgu.rasp.util

import ru.mpgu.rasp.data.remote.dto.ManifestGroupDto

/**
 * Каталог групп для навигации: институт → направление → профиль → группа.
 *
 * Студент помнит своё направление и профиль, а не код группы, поэтому список
 * строится по ним. Источники, которые направление не публикуют, всё равно
 * попадают в каталог — в хвостовую секцию [NO_DIRECTION]: потерять группу
 * хуже, чем показать её без направления.
 */
object GroupCatalog {

    const val NO_DIRECTION = "Без направления"
    const val NO_PROFILE = "Без профиля"

    data class ProfileNode(val profile: String, val groups: List<ManifestGroupDto>)
    data class DirectionNode(val direction: String, val profiles: List<ProfileNode>)

    fun build(groups: List<ManifestGroupDto>): List<DirectionNode> {
        val byDirection = groups.groupBy { it.direction?.takeIf(String::isNotBlank) ?: NO_DIRECTION }
        return byDirection.entries
            .sortedWith(compareBy({ it.key == NO_DIRECTION }, { it.key }))
            .map { (direction, dirGroups) ->
                val profiles = dirGroups
                    .groupBy { it.profile?.takeIf(String::isNotBlank) ?: NO_PROFILE }
                    .entries
                    .sortedWith(compareBy({ it.key == NO_PROFILE }, { it.key }))
                    .map { (profile, list) ->
                        ProfileNode(
                            profile,
                            list.sortedWith(compareBy({ it.year ?: 0 }, { it.name })),
                        )
                    }
                DirectionNode(direction, profiles)
            }
    }

    /**
     * Поиск по направлению, профилю и коду группы сразу. Код по-прежнему
     * матчится через [GroupSearch] (гомоглифы), текстовые поля — обычным
     * подстрочным сравнением без регистра.
     */
    fun filter(groups: List<ManifestGroupDto>, query: String): List<ManifestGroupDto> {
        if (query.isBlank()) return groups
        val text = query.trim().lowercase()
        val code = GroupSearch.searchKey(query)
        return groups.filter { g ->
            GroupSearch.searchKey(g.name).contains(code) ||
                g.direction?.lowercase()?.contains(text) == true ||
                g.profile?.lowercase()?.contains(text) == true
        }
    }
}
