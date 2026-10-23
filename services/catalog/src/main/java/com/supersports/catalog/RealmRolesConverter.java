package com.supersports.catalog;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;

final class RealmRolesConverter implements Converter<Jwt, Collection<GrantedAuthority>> {
    @Override
    public Collection<GrantedAuthority> convert(Jwt jwt) {
        Object claim = jwt.getClaims().get("realm_access");
        if (!(claim instanceof Map<?, ?> realm) || !(realm.get("roles") instanceof List<?> roles)) {
            return List.of();
        }
        var authorities = new LinkedHashSet<GrantedAuthority>();
        for (Object value : roles) {
            if (!(value instanceof String role) || role.isBlank()) {
                return List.of();
            }
            authorities.add(new SimpleGrantedAuthority("ROLE_" + role));
        }
        return List.copyOf(authorities);
    }
}
