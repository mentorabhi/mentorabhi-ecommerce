package com.supersports.catalog;

import java.net.URI;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;

/** Sourced facts are plain text; all runtime image references are local photo keys. */
record ProductDetails(String model, String equipmentType, List<String> highlights, String material,
                      String intendedUse, String fit, String care, List<String> packageContents,
                      Provenance provenance, List<Photo> gallery, String commerceProvenance) {
    record Provenance(String sourceUrl, String capturedOn, String rightsStatement) {}
    record Photo(String assetKey, String altText, String kind) {}

    ProductDetails validated() {
        text(model, "model", 200, true);
        text(equipmentType, "equipmentType", 80, true);
        for (String value : new String[]{material,intendedUse,fit,care,commerceProvenance}) text(value,"detail text",2000,false);
        strings(highlights,"highlights"); strings(packageContents,"packageContents");
        if (provenance == null) throw new IllegalArgumentException("provenance is required");
        text(provenance.rightsStatement(),"rightsStatement",2000,true);
        sourceUrl(provenance.sourceUrl());
        try { LocalDate.parse(provenance.capturedOn()); }
        catch (DateTimeParseException | NullPointerException e) { throw new IllegalArgumentException("capturedOn must be an ISO date"); }
        if (gallery == null || gallery.isEmpty() || gallery.size()>8) throw new IllegalArgumentException("gallery needs 1 to 8 photographs");
        for (Photo photo : gallery) {
            if(photo==null || !"photograph".equals(photo.kind())) throw new IllegalArgumentException("gallery kind must be photograph");
            if(photo.assetKey()==null || photo.assetKey().length()>200 || !photo.assetKey().matches("[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*\\.(jpg|jpeg|png|webp)"))
                throw new IllegalArgumentException("gallery assetKey must be a relative local photograph key");
            text(photo.altText(),"altText",240,true);
        }
        return this;
    }
    private static void strings(List<String> values,String name) {
        if(values==null || values.size()>20) throw new IllegalArgumentException(name+" must be a list of at most 20 strings");
        for(String value:values) text(value,name,500,true);
    }
    static void text(String value,String name,int max,boolean required) {
        if(value==null ? required : (required && value.isBlank()) || value.length()>max || value.codePoints().anyMatch(c->Character.isISOControl(c) && c!='\n' && c!='\t') || value.contains("<") || value.contains(">"))
            throw new IllegalArgumentException(name+" must be plain text, at most "+max+" characters");
    }
    private static void sourceUrl(String value) {
        try {
            URI uri=URI.create(value);
            if(value.length()>2000 || !("https".equals(uri.getScheme()) || "http".equals(uri.getScheme())) || uri.getHost()==null || uri.getUserInfo()!=null)
                throw new IllegalArgumentException();
        } catch (IllegalArgumentException | NullPointerException e) { throw new IllegalArgumentException("sourceUrl must be an absolute HTTP(S) attribution URL without credentials"); }
    }
}
