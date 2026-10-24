package com.supersports.orderhistory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Retained Kafka evidence, excluding records explicitly quarantined in the DLQ. */
final class ProjectionEventIndex {
    private final Map<String,Entry> records=new LinkedHashMap<>();
    private final Map<String,Map<String,Object>> rejected=new LinkedHashMap<>();
    private final Set<String> sourceConflicts=new LinkedHashSet<>();

    void add(String coordinate,String raw) {
        String rawHash=EventContent.rawHash(raw);
        try {
            var event=HistoryRules.parse(EventContent.read(raw));
            records.put(coordinate,new Entry(event.eventId().toString(),EventContent.hash(raw),rawHash));
        } catch (RuntimeException error) {
            records.put(coordinate,new Entry(null,null,rawHash));
            quarantine(coordinate,"INVALID_EVENT",rawHash);
        }
    }

    void quarantine(String coordinate,String code,String rawHash) {
        var source=records.get(coordinate);
        if (source==null || !source.rawHash().equals(rawHash)) sourceConflicts.add("DLQ_SOURCE_CONTENT_MISMATCH:"+coordinate);
        rejected.put(coordinate,Map.of("coordinate",coordinate,"code",code,"rawHash",rawHash));
    }

    List<Map<String,Object>> events() {
        Map<String,Entry> unique=new LinkedHashMap<>();Map<String,Set<String>> raw=new LinkedHashMap<>();
        records.forEach((coordinate,event)->{
            if(event.eventId()!=null && !rejected.containsKey(coordinate)) {
                unique.putIfAbsent(event.eventId(),event);
                raw.computeIfAbsent(event.eventId(),id->new LinkedHashSet<>()).add(event.rawHash());
            }
        });
        return unique.values().stream().map(event->Map.<String,Object>of("eventId",event.eventId(),"canonicalHash",event.canonicalHash(),"rawHashes",raw.get(event.eventId()))).toList();
    }

    List<String> conflicts() {
        Set<String> conflicts=new LinkedHashSet<>(sourceConflicts);Map<String,String> hashes=new LinkedHashMap<>();
        records.forEach((coordinate,event)->{
            if(event.eventId()!=null && !rejected.containsKey(coordinate)) {
                String prior=hashes.putIfAbsent(event.eventId(),event.canonicalHash());
                if(prior!=null && !prior.equals(event.canonicalHash()))conflicts.add("EVENT_ID_CONTENT_CONFLICT:"+event.eventId());
            }
        });
        return List.copyOf(conflicts);
    }
    List<Map<String,Object>> poison(){return new ArrayList<>(rejected.values());}
    record Entry(String eventId,String canonicalHash,String rawHash) {}
}
