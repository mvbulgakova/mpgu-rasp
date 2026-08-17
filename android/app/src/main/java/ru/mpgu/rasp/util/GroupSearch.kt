package ru.mpgu.rasp.util

object GroupSearch {
    // Same table as cloudflare-worker-bot/worker.js and Python scraper.
    private val HOMO = mapOf(
        'A' to 'А', 'B' to 'В', 'C' to 'С', 'E' to 'Е', 'H' to 'Н',
        'K' to 'К', 'M' to 'М', 'O' to 'О', 'P' to 'Р', 'T' to 'Т',
        'X' to 'Х', 'Y' to 'У',
    )
    private val STRIP = Regex("[\\s\\-_]")

    fun searchKey(input: String): String {
        val upper = input.trim().uppercase()
        val folded = buildString(upper.length) {
            for (c in upper) append(HOMO[c] ?: c)
        }
        return STRIP.replace(folded, "")
    }

    fun filter(groups: List<String>, query: String): List<String> {
        if (query.isBlank()) return groups
        val key = searchKey(query)
        return groups.filter { searchKey(it).contains(key) }
    }
}
