package ru.mpgu.rasp.util

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class GroupSearchTest {

    @Test fun `latin lookalikes fold to cyrillic`() {
        // All five letters in "BOEHK" have Cyrillic homoglyphs
        // (B→В, O→О, E→Е, H→Н, K→К).
        assertEquals("ВОЕНК", GroupSearch.searchKey("BOEHK"))
    }

    @Test fun `whitespace and separators are stripped`() {
        // Cyrillic-only input — no folding needed, only strip+uppercase.
        assertEquals("ВОП40ПФК2501", GroupSearch.searchKey(" ВОП 40 - ПФК_2501 "))
    }

    @Test fun `lowercase is uppercased before folding`() {
        assertEquals("ВОЕНК", GroupSearch.searchKey("boehk"))
    }

    @Test fun `mixed-script query matches full cyrillic group`() {
        // Real UX: user reads "ВОП40-ПФК2501" off a poster and types the
        // homoglyph-safe prefix in Latin (BO → ВО), keeping the rest in
        // Cyrillic because П and Ф have no Latin look-alikes.
        val groups = listOf("ВОП40-ПФК2501", "ГПОФ01-ГЕО2501")
        val hits = GroupSearch.filter(groups, "BOП40")
        assertTrue("ВОП40-ПФК2501" in hits)
        assertTrue("ГПОФ01-ГЕО2501" !in hits)
    }

    @Test fun `numeric query filters`() {
        val groups = listOf("ВОП40-ПФК2501", "ГПОФ01-ГЕО2501")
        val hits = GroupSearch.filter(groups, "40")
        assertTrue("ВОП40-ПФК2501" in hits)
        assertTrue("ГПОФ01-ГЕО2501" !in hits)
    }
}
