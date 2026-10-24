package com.supersports.orderhistory;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name="order-history.operator-mode",havingValue="true")
class OperatorRunner implements ApplicationRunner {
    private final ReplayOperations replay;
    private final ProjectionOperations projection;
    private final boolean enabled;
    private final String jwks,issuer;
    private int exitCode;
    OperatorRunner(ReplayOperations replay,ProjectionOperations projection,@Value("${order-history.operator-enabled:false}") boolean enabled,
                   @Value("${order-history.operator-jwks:http://identity:8080/realms/supersports/protocol/openid-connect/certs}") String jwks,
                   @Value("${order-history.operator-issuer:http://localhost:8180/realms/supersports}") String issuer) {
        this.replay=replay;this.projection=projection;this.enabled=enabled;this.jwks=jwks;this.issuer=issuer;
    }

    @Override public void run(ApplicationArguments arguments) {
        try {
            if (!enabled) throw new IllegalArgumentException("OPERATOR_MODE_DISABLED");
            byte[] input=System.in.readNBytes(1_048_577);
            if (input.length>1_048_576) throw new IllegalArgumentException("OPERATOR_REQUEST_TOO_LARGE");
            var request=EventContent.read(new String(input,StandardCharsets.UTF_8));
            String subject=authenticate(request.get("token"));
            Object action=request.get("action");
            Map<String,Object> result=switch(String.valueOf(action)) {
                case "demo-poison" -> replay.demo();
                case "replay" -> replay.replay(request,subject);
                case "snapshot" -> projection.snapshot();
                case "inspect" -> projection.inspect();
                case "rebuild" -> projection.rebuild(Boolean.TRUE.equals(request.get("injectMismatch")));
                default -> throw new IllegalArgumentException("UNKNOWN_OPERATOR_ACTION");
            };
            System.out.println("SUPERSPORTS_OPERATOR_RESULT "+EventContent.write(Map.of("ok",true,"result",result)));
        } catch (Exception error) {
            exitCode=2;
            String code=error.getMessage();
            if (code==null || !code.matches("[A-Z_]{3,80}")) code="OPERATOR_OPERATION_FAILED";
            System.out.println("SUPERSPORTS_OPERATOR_RESULT "+EventContent.write(Map.of("ok",false,"error",code)));
        }
    }

    private String authenticate(Object raw) {
        if (!(raw instanceof String token) || token.isBlank()) throw new IllegalArgumentException("OPERATOR_AUTHENTICATION_REQUIRED");
        try {
            var decoder=NimbusJwtDecoder.withJwkSetUri(jwks).build();
            decoder.setJwtValidator(JwtValidators.createDefaultWithIssuer(issuer));
            var jwt=decoder.decode(token);
            if (!jwt.getAudience().contains("supersports-api") || jwt.getSubject()==null) throw new IllegalArgumentException();
            return jwt.getSubject();
        } catch (RuntimeException error) { throw new IllegalArgumentException("OPERATOR_AUTHENTICATION_REQUIRED"); }
    }
    int exitCode() { return exitCode; }
}
