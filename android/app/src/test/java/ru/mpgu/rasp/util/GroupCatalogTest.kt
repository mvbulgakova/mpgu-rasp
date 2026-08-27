package ru.mpgu.rasp.util

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import ru.mpgu.rasp.data.remote.dto.ManifestGroupDto

class GroupCatalogTest {

    private fun g(
        name: String,
        direction: String? = null,
        profile: String? = null,
        year: Int? = null,
    ) = ManifestGroupDto(
        name = name, file = name, year = year,
        form = "full_time", degree = "bachelor",
        direction = direction, profile = profile,
    )

    @Test fun `groups are catalogued by direction then profile`() {
        // Студент не помнит код группы — он знает своё направление и профиль.
        val groups = listOf(
            g("БОЖ09-ЖРН2101", "42.03.02 ЖУРНАЛИСТИКА", "Журналистика", 1),
            g("БОЖ09-ЖРН2102", "42.03.02 ЖУРНАЛИСТИКА", "Журналистика", 1),
            g("БОЖ09-МХК2101", "44.03.01 ПЕДАГОГИЧЕСКОЕ ОБРАЗОВАНИЕ", "МХК", 1),
        )
        val cat = GroupCatalog.build(groups)

        assertEquals(
            listOf("42.03.02 ЖУРНАЛИСТИКА", "44.03.01 ПЕДАГОГИЧЕСКОЕ ОБРАЗОВАНИЕ"),
            cat.map { it.direction },
        )
        assertEquals(listOf("Журналистика"), cat[0].profiles.map { it.profile })
        assertEquals(
            listOf("БОЖ09-ЖРН2101", "БОЖ09-ЖРН2102"),
            cat[0].profiles[0].groups.map { it.name },
        )
    }

    @Test fun `groups without a direction land in a fallback section, never dropped`() {
        // Часть источников не публикует шапку с направлением. Терять такие
        // группы нельзя — они уходят в секцию «Без направления», и она идёт
        // последней, чтобы не мешать нормальной навигации.
        val groups = listOf(
            g("БОЖ09-ЖРН2101", "42.03.02 ЖУРНАЛИСТИКА", "Журналистика"),
            g("ЗФБ-ГЕО2201"),
        )
        val cat = GroupCatalog.build(groups)

        assertEquals(2, cat.size)
        assertEquals(GroupCatalog.NO_DIRECTION, cat.last().direction)
        assertEquals(listOf("ЗФБ-ГЕО2201"), cat.last().profiles[0].groups.map { it.name })
    }

    @Test fun `search matches direction and profile, not only the code`() {
        val groups = listOf(
            g("БОЖ09-ЖРН2101", "42.03.02 ЖУРНАЛИСТИКА", "Телевидение"),
            g("БОЖ09-МХК2101", "44.03.01 ПЕДАГОГИЧЕСКОЕ ОБРАЗОВАНИЕ", "МХК"),
        )
        assertEquals(
            listOf("БОЖ09-ЖРН2101"),
            GroupCatalog.filter(groups, "журналист").map { it.name },
        )
        assertEquals(
            listOf("БОЖ09-ЖРН2101"),
            GroupCatalog.filter(groups, "телевидение").map { it.name },
        )
        // Код группы по-прежнему ищется, с гомоглифами (BOЖ → БОЖ).
        assertEquals(
            listOf("БОЖ09-ЖРН2101"),
            GroupCatalog.filter(groups, "BOЖ09").map { it.name },
        )
    }

    @Test fun `profile-less groups inside a direction keep a stable bucket`() {
        val groups = listOf(
            g("БОЖ09-ЖРН2101", "42.03.02 ЖУРНАЛИСТИКА", null),
            g("БОЖ09-ЖРН2102", "42.03.02 ЖУРНАЛИСТИКА", "Журналистика"),
        )
        val cat = GroupCatalog.build(groups)
        assertEquals(1, cat.size)
        assertEquals(2, cat[0].profiles.size)
        assertTrue(cat[0].profiles.any { it.profile == GroupCatalog.NO_PROFILE })
    }
}
