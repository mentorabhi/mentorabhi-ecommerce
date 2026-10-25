package com.supersports.catalog;

import java.util.*;
import java.util.regex.Pattern;

/** Deterministic query interpretation; no generated SQL or model inference. */
record CatalogSearch(String terms, String equipment, String equipmentWords, String rankingTerms, boolean noMatch, String literal) {
    private static final Pattern WORD = Pattern.compile("[\\p{L}\\p{N}]+");
    private static final Set<String> FILLER = Set.of("a","an","the","for","show","me","find");
    private static final Map<String,String> EQUIPMENT = Map.ofEntries(
        Map.entry("bat","bat"),Map.entry("bats","bat"),Map.entry("ball","ball"),Map.entry("balls","ball"),
        Map.entry("pad","pads"),Map.entry("pads","pads"),Map.entry("glove","gloves"),Map.entry("gloves","gloves"),
        Map.entry("helmet","helmet"),Map.entry("helmets","helmet"),Map.entry("bag","bag"),Map.entry("bags","bag"),
        Map.entry("kit","kit"),Map.entry("kits","kit"),Map.entry("jersey","jersey"),Map.entry("jerseys","jersey"),
        Map.entry("shirt","shirt"),Map.entry("shirts","shirt"),Map.entry("jacket","jacket"),Map.entry("jackets","jacket"),
        Map.entry("hoodie","hoodie"),Map.entry("hoodies","hoodie"),Map.entry("boot","boots"),Map.entry("boots","boots"),
        Map.entry("sock","socks"),Map.entry("socks","socks"));

    static CatalogSearch parse(String query) {
        var words = WORD.matcher(query.toLowerCase(Locale.ROOT)).results().map(match->match.group())
                .filter(word->!FILLER.contains(word)).distinct().toList();
        var types = words.stream().map(EQUIPMENT::get).filter(Objects::nonNull).distinct().toList();
        String equipment = types.size()==1 ? types.getFirst() : null;
        var terms = words.stream().filter(word->equipment==null || !equipment.equals(EQUIPMENT.get(word))).toList();
        String aliases = equipment==null ? "" : String.join("|",EQUIPMENT.entrySet().stream()
                .filter(entry->entry.getValue().equals(equipment)).map(Map.Entry::getKey).sorted().toList());
        return new CatalogSearch(String.join(" ",terms),equipment,"\\m("+aliases+")\\M",
                String.join(" ",words.stream().map(word->EQUIPMENT.getOrDefault(word,word)).toList()),words.isEmpty(), query.matches("(?s).*[%_!].*") ? query.trim() : null);
    }
}
