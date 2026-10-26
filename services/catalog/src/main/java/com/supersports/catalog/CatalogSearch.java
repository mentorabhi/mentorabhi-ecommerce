package com.supersports.catalog;

import java.util.*;
import java.util.regex.Pattern;

/** Deterministic query interpretation; no generated SQL or model inference. */
record CatalogSearch(String terms, String equipment, String equipmentWords, String rankingTerms, boolean noMatch, String literal, String equipmentTypePattern) {
    private static final Pattern WORD = Pattern.compile("[\\p{L}\\p{N}]+");
    private static final Set<String> FILLER = Set.of("a","an","the","for","show","me","find");
    private static final Map<String,String> COMPOUND = Map.ofEntries(
        Map.entry("bat grip","bat-grip"),Map.entry("bat grips","bat-grip"),
        Map.entry("bat oil","bat-oil"),Map.entry("linseed oil","bat-oil"),
        Map.entry("bat toe guard","toe-guard"),Map.entry("toe guard","toe-guard"),
        Map.entry("batting tee","batting-tee"),Map.entry("batting tees","batting-tee"),
        Map.entry("bat care kit","bat-care-kit"),Map.entry("bat repair kit","bat-care-kit"),
        Map.entry("padded shorts","padded-inners"),Map.entry("protective shorts","padded-inners"),Map.entry("batting inners","padded-inners"),
        Map.entry("inner thigh guard","inner-thigh-guard"),Map.entry("inner thigh pad","inner-thigh-guard"),
        Map.entry("fielding shin guards","fielding-shin-guards"),Map.entry("shin guards","fielding-shin-guards"),Map.entry("shin guard","fielding-shin-guards"));
    private static final Map<String,String> EQUIPMENT = Map.ofEntries(
        Map.entry("bat","bat"),Map.entry("bats","bat"),Map.entry("ball","ball"),Map.entry("balls","ball"),
        Map.entry("pad","pads"),Map.entry("pads","pads"),Map.entry("glove","gloves"),Map.entry("gloves","gloves"),
        Map.entry("helmet","helmet"),Map.entry("helmets","helmet"),Map.entry("bag","bag"),Map.entry("bags","bag"),
        Map.entry("kit","kit"),Map.entry("kits","kit"),Map.entry("jersey","jersey"),Map.entry("jerseys","jersey"),
        Map.entry("shirt","shirt"),Map.entry("shirts","shirt"),Map.entry("jacket","jacket"),Map.entry("jackets","jacket"),
        Map.entry("hoodie","hoodie"),Map.entry("hoodies","hoodie"),Map.entry("boot","boots"),Map.entry("boots","boots"),
        Map.entry("sock","socks"),Map.entry("socks","socks"),
        Map.entry("shoe","boots"),Map.entry("shoes","boots"));

    static CatalogSearch parse(String query) {
        var words = WORD.matcher(query.toLowerCase(Locale.ROOT).replace("wicketkeeping", "wicket keeping")).results().map(match->match.group())
                .filter(word->!FILLER.contains(word)).toList();
        String remaining=" "+String.join(" ",words)+" ";
        var types=new LinkedHashSet<String>();
        for(var phrase:COMPOUND.keySet().stream().sorted(Comparator.comparingInt(String::length).reversed().thenComparing(Comparator.naturalOrder())).toList()) {
            String bounded=" "+phrase+" ";
            if(remaining.contains(bounded)) {
                types.add(COMPOUND.get(phrase));
                remaining=remaining.replace(bounded," ");
            }
        }
        var remainingWords=Arrays.stream(remaining.trim().split(" +")).filter(word->!word.isEmpty()).toList();
        remainingWords.stream().map(EQUIPMENT::get).filter(Objects::nonNull).forEach(types::add);
        String equipment = types.size()==1 ? types.iterator().next() : null;
        var terms = (equipment==null ? words : remainingWords).stream().filter(word->equipment==null || !equipment.equals(EQUIPMENT.get(word))).toList();
        var aliases=new TreeSet<String>();
        if(equipment!=null) {
            aliases.add(equipment);
            EQUIPMENT.forEach((word,type)->{if(type.equals(equipment))aliases.add(word);});
            COMPOUND.forEach((phrase,type)->{if(type.equals(equipment))aliases.add(phrase);});
        }
        String alternatives=String.join("|",aliases);
        return new CatalogSearch(String.join(" ",terms),equipment,"\\m("+alternatives+")\\M",
                String.join(" ",words.stream().map(word->EQUIPMENT.getOrDefault(word,word)).toList()),words.isEmpty(), query.matches("(?s).*[%_!].*") ? query.trim() : null,
                "^("+alternatives+")$");
    }
}
