package com.supersports.orderhistory;

import java.util.List;
import java.util.Map;

final class ReplayRules {
    private ReplayRules() {}
    static Coordinate coordinate(String raw, String topic) {
        String[] parts = raw.split(":", -1);
        if (parts.length != 3 || !parts[0].equals(topic) || !parts[1].matches("[0-9]+") || !parts[2].matches("[0-9]+"))
            throw new IllegalArgumentException("INVALID_SOURCE_COORDINATE");
        try { return new Coordinate(topic, Integer.parseInt(parts[1]), Long.parseLong(parts[2])); }
        catch (NumberFormatException error) { throw new IllegalArgumentException("INVALID_SOURCE_COORDINATE"); }
    }

    static HistoryRules.Event correction(String original, String corrected) {
        var before = EventContent.read(original);
        var after = EventContent.read(corrected);
        for (String key : List.of("eventId", "aggregateId", "aggregateSequence", "customerKey")) {
            if (before.get(key) == null || after.get(key) == null ||
                    !EventContent.hash(EventContent.write(Map.of(key,before.get(key)))).equals(EventContent.hash(EventContent.write(Map.of(key,after.get(key))))))
                throw new IllegalArgumentException("REPLAY_IDENTITY_CHANGE");
        }
        return HistoryRules.parse(after);
    }

    record Coordinate(String topic, int partition, long offset) {
        @Override public String toString() { return topic + ":" + partition + ":" + offset; }
    }
}
