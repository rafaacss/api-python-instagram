import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const respTime = new Trend('resp_time', true);

const BASE_URL = __ENV.TARGET_URL;
const TEST_TYPE = __ENV.TEST_TYPE || 'homepage';
const ENDPOINTS = __ENV.ENDPOINTS ? __ENV.ENDPOINTS.split(',') : ['/'];
const LOGIN_URL = __ENV.LOGIN_URL || '';
const LOGIN_USER = __ENV.LOGIN_USER || '';
const LOGIN_PASS = __ENV.LOGIN_PASS || '';
const LOGIN_USER_FIELD = __ENV.LOGIN_USER_FIELD || 'email';
const LOGIN_PASS_FIELD = __ENV.LOGIN_PASS_FIELD || 'password';

export const options = {
    vus: parseInt(__ENV.VUS) || 10,
    duration: __ENV.DURATION || '30s',
    thresholds: {
        http_req_duration: ['p(95)<10000'],
        errors: ['rate<0.5'],
    },
};

// Store cookies/token after login
let authCookies = null;
let authToken = null;

export function setup() {
    if (TEST_TYPE === 'authenticated' && LOGIN_URL && LOGIN_USER) {
        console.log(`[LOGIN] Tentando autenticacao em: ${LOGIN_URL}`);
        console.log(`[LOGIN] Usuario: ${LOGIN_USER}`);
        console.log(`[LOGIN] Campos: ${LOGIN_USER_FIELD}/${LOGIN_PASS_FIELD}`);

        const loginPayload = {};
        loginPayload[LOGIN_USER_FIELD] = LOGIN_USER;
        loginPayload[LOGIN_PASS_FIELD] = LOGIN_PASS;

        // Try JSON login first
        console.log('[LOGIN] Tentando login via JSON...');
        let res = http.post(LOGIN_URL, JSON.stringify(loginPayload), {
            headers: { 'Content-Type': 'application/json' },
            redirects: 0,
        });
        let loginMethod = 'JSON';

        // If JSON didn't work (non-2xx), try form-encoded
        if (res.status >= 400) {
            console.log(`[LOGIN] JSON retornou ${res.status}, tentando form-encoded...`);
            res = http.post(LOGIN_URL, loginPayload, {
                redirects: 0,
            });
            loginMethod = 'form-encoded';
        }

        console.log(`[LOGIN] Status HTTP: ${res.status} (via ${loginMethod})`);

        const cookies = res.cookies;
        let token = null;

        // Count cookies received
        const cookieNames = Object.keys(cookies || {});
        if (cookieNames.length > 0) {
            console.log(`[LOGIN] Cookies recebidos (${cookieNames.length}): ${cookieNames.join(', ')}`);
        } else {
            console.log('[LOGIN] Nenhum cookie recebido');
        }

        // Try to extract token from response body
        try {
            const body = JSON.parse(res.body);
            token = body.token || body.access_token || body.jwt || body.data?.token || body.data?.access_token || null;
            if (token) {
                console.log(`[LOGIN] TOKEN OBTIDO com sucesso (${token.substring(0, 20)}...)`);
            } else {
                console.log('[LOGIN] Resposta JSON parseada, mas nenhum campo de token encontrado');
                console.log(`[LOGIN] Campos disponiveis: ${Object.keys(body).join(', ')}`);
            }
        } catch (e) {
            // Not JSON, check for token in headers
            const authHeader = res.headers['Authorization'] || res.headers['authorization'];
            if (authHeader) {
                token = authHeader.replace('Bearer ', '');
                console.log(`[LOGIN] Token obtido via header Authorization`);
            } else {
                console.log('[LOGIN] Resposta nao e JSON e sem header Authorization');
            }
        }

        // Final login status
        const isSuccess = res.status >= 200 && res.status < 400;
        const hasAuth = token || cookieNames.length > 0;

        if (isSuccess && hasAuth) {
            console.log(`[LOGIN] *** LOGIN BEM SUCEDIDO *** (HTTP ${res.status}, ${token ? 'com token' : `com ${cookieNames.length} cookies`})`);
        } else if (isSuccess) {
            console.log(`[LOGIN] *** ATENCAO: HTTP ${res.status} mas sem token/cookies - autenticacao pode ter falhado ***`);
        } else {
            console.log(`[LOGIN] *** LOGIN FALHOU *** (HTTP ${res.status})`);
            console.log(`[LOGIN] Response body (primeiros 500 chars): ${(res.body || '').substring(0, 500)}`);
        }

        return { cookies, token, loginSuccess: isSuccess && hasAuth };
    }
    return {};
}

function getRequestParams(data) {
    const params = {
        headers: {},
        tags: {},
    };

    if (data && data.token) {
        params.headers['Authorization'] = `Bearer ${data.token}`;
    }

    return params;
}

export default function (data) {
    const params = getRequestParams(data);

    if (TEST_TYPE === 'homepage') {
        group('Homepage Load', () => {
            const res = http.get(BASE_URL, params);
            check(res, {
                'status 200': (r) => r.status === 200,
                'body not empty': (r) => r.body && r.body.length > 0,
                'load < 3s': (r) => r.timings.duration < 3000,
            });
            errorRate.add(res.status !== 200);
            respTime.add(res.timings.duration);
        });
    }

    if (TEST_TYPE === 'endpoints' || TEST_TYPE === 'authenticated') {
        ENDPOINTS.forEach((endpoint) => {
            const ep = endpoint.trim();
            group(`Endpoint: ${ep}`, () => {
                const url = ep.startsWith('http') ? ep : `${BASE_URL}${ep}`;
                const res = http.get(url, params);
                check(res, {
                    [`${ep} status OK`]: (r) => r.status >= 200 && r.status < 400,
                    [`${ep} has body`]: (r) => r.body && r.body.length > 0,
                });
                errorRate.add(res.status >= 400);
                respTime.add(res.timings.duration);
            });
        });
    }

    if (TEST_TYPE === 'full') {
        // Test homepage
        group('Homepage', () => {
            const res = http.get(BASE_URL, params);
            check(res, { 'homepage 200': (r) => r.status === 200 });
            errorRate.add(res.status !== 200);
            respTime.add(res.timings.duration);
        });

        // Test all endpoints
        ENDPOINTS.forEach((endpoint) => {
            const ep = endpoint.trim();
            if (ep && ep !== '/') {
                group(`Endpoint: ${ep}`, () => {
                    const url = ep.startsWith('http') ? ep : `${BASE_URL}${ep}`;
                    const res = http.get(url, params);
                    check(res, {
                        [`${ep} OK`]: (r) => r.status >= 200 && r.status < 400,
                    });
                    errorRate.add(res.status >= 400);
                    respTime.add(res.timings.duration);
                });
            }
        });
    }

    sleep(parseFloat(__ENV.SLEEP || '0.5'));
}

export function handleSummary(data) {
    const groups = {};
    if (data.root_group && data.root_group.groups) {
        for (const g of data.root_group.groups) {
            const gMetrics = {};
            if (g.checks) {
                gMetrics.checks = g.checks.map((c) => ({
                    name: c.name,
                    passes: c.passes,
                    fails: c.fails,
                }));
            }
            groups[g.name] = gMetrics;
        }
    }

    const summary = {
        target_url: BASE_URL,
        test_type: TEST_TYPE,
        vus: options.vus,
        duration: options.duration,
        metrics: {
            http_req_duration: {
                avg: data.metrics.http_req_duration?.values?.avg || 0,
                min: data.metrics.http_req_duration?.values?.min || 0,
                max: data.metrics.http_req_duration?.values?.max || 0,
                p90: data.metrics.http_req_duration?.values['p(90)'] || 0,
                p95: data.metrics.http_req_duration?.values['p(95)'] || 0,
                med: data.metrics.http_req_duration?.values?.med || 0,
            },
            http_reqs: {
                count: data.metrics.http_reqs?.values?.count || 0,
                rate: data.metrics.http_reqs?.values?.rate || 0,
            },
            http_req_failed: {
                rate: data.metrics.http_req_failed?.values?.rate || 0,
            },
            iterations: {
                count: data.metrics.iterations?.values?.count || 0,
                rate: data.metrics.iterations?.values?.rate || 0,
            },
            resp_time: {
                avg: data.metrics.resp_time?.values?.avg || 0,
                min: data.metrics.resp_time?.values?.min || 0,
                max: data.metrics.resp_time?.values?.max || 0,
                p90: data.metrics.resp_time?.values['p(90)'] || 0,
                p95: data.metrics.resp_time?.values['p(95)'] || 0,
            },
            errors: {
                rate: data.metrics.errors?.values?.rate || 0,
            },
        },
        groups,
    };

    return {
        stdout: JSON.stringify(summary, null, 2),
    };
}
