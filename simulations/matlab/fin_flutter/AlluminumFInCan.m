%% =======================================================================
% FAST 10k COTS – Fin & Stability Tool (from OpenRocket CSV)
%
%  - Reads IREC.csv (Time, Altitude, Total velocity)
%  - Finds max velocity and its altitude
%  - Uses current 4.02" Max Q aluminum fin geometry
%  - Computes:
%       * Fin area, AR, taper, t/c
%       * Barrowman CP (optional cross-check)
%       * Static margin
%       * Flutter boundary (Martin/Apogee)
%
% Units:
%   Geometry: in
%   Atmosphere & velocities: ft, ft/s, psi, °R
% =======================================================================

clear; clc;

%% -------------------- CONSTANTS ----------------------------------------
g       = 32.174;          % [ft/s^2]
gamma   = 1.4;             % [-]
R_air   = 1716.49;         % [ft*lbf/(slug*R)]

T0      = 518.67;          % [R]
P0_psf  = 2116;            % [lb/ft^2]
P0_psi  = P0_psf / 144;    % [psi]
L_lapse = 0.00356616;      % [R/ft]

%% -------------------- IMPORT TRAJECTORY FROM OPENROCKET ---------------
csvPath = 'IREC.csv';   % <-- make sure this filename matches your export

T = readtable(csvPath, ...
    'FileType','text', ...
    'CommentStyle','#', ...
    'ReadVariableNames',false);

T.Properties.VariableNames = {'t','h','V'};  % Time, Altitude, Velocity

% Max velocity and altitude at that point
[V_max, idxMax] = max(T.V);
h_max           = T.h(idxMax);

%% -------------------- ROCKET GEOMETRY (UPDATE AS NEEDED) --------------
D_body_in   = 4.02;        % [in] body OD from OR
L_rocket_in = 84.0;        % [in] approximate overall length

% Nose length = exposed length from tip to body-tube joint (NOT coupler)
L_nose_in   = 16.0;        % [in] TODO: measure actual nose and update

% Mass properties from OpenRocket
CG_from_tip_in_OR = 54.62;    % [in] CG (prepped)
CP_from_tip_in_OR = 65.208;    % [in] CP
SM_calibers_OR    = (CP_from_tip_in_OR - CG_from_tip_in_OR) / D_body_in;

% Use OR CG as reference CG for Barrowman comparison
CG_from_tip_in = CG_from_tip_in_OR;

% OPTIONAL (for Barrowman CP cross-check):
% Distance from nose tip to fin root leading edge along body tube.
Xf_le_from_tip_in = 70.5;      % [in] estimate; update when known

%% -------------------- MAX Q AEROSPACE 4" FIN GEOMETRY -----------------
% Actual polygon points from your Freeform Fin Set (inches):
% (0,0) -> (9.69,5) -> (12.5,3.74) -> (13.26,0) -> back to (0,0)
x = [0,    9.69, 12.5, 13.26];
y = [0,    5.00, 3.74, 0.00];

% Planform area via shoelace formula
x_shift = circshift(x, -1);
y_shift = circshift(y, -1);
S_fin_in2 = 0.5 * abs(sum(x .* y_shift - y .* x_shift));   % [in^2]

span_in = max(y);                 % [in] max height off body = 5.0
n_fins  = 3;                      % 3-fin configuration
t_in    = 0.118;                  % [in] thickness (aluminum)

% Equivalent trapezoid for flutter calc:
cr_in   = max(x) - min(x);        % [in] root chord ~ 13.26 (0 to 13.26)
ct_in   = 2*S_fin_in2/span_in - cr_in;  % [in] set so area matches

AR       = span_in^2 / S_fin_in2; % [-] aspect ratio
lambda   = ct_in / cr_in;         % [-] taper ratio
t_over_c = t_in  / cr_in;         % [-] thickness ratio

%% -------------------- ATMOSPHERE AT h_max ------------------------------
T_R   = T0 - L_lapse * h_max;          % [R]
theta = T_R / T0;
P_psf = P0_psf * theta^5.2561;         % [lb/ft^2]
P_psi = P_psf / 144;                   % [psi]

a_sos = sqrt(gamma * R_air * T_R);     % [ft/s]
M_max = V_max / a_sos;                 % [-]

%% -------------------- BARROWMAN CP (OPTIONAL) --------------------------
D_body_ft = D_body_in / 12;

% Nose contribution (ogive)
CNalpha_nose = 2.0;
Xcp_nose_in  = 0.466 * L_nose_in;

% Finset contribution (approx. treating as trapezoid with cr, ct, span)
lm_in = 0.5 * (cr_in + ct_in);        % mid-chord length
K_fb  = 1 + (D_body_in/2) / (span_in + D_body_in/2);

CNalpha_fins = K_fb * ...
    (4 * n_fins * (span_in / D_body_in)^2) / ...
    (1 + sqrt(1 + (2*lm_in/(cr_in + ct_in))^2));

Xf_le_in = Xf_le_from_tip_in; % shorthand

term1 = lm_in * (cr_in + 2*ct_in) / (3*(cr_in + ct_in));
term2 = (cr_in + ct_in - (cr_in*ct_in)/(cr_in + ct_in)) / 6;
Xcp_fins_in = Xf_le_in + term1 + term2;

CNalpha_total = CNalpha_nose + CNalpha_fins;
Xcp_total_in  = (CNalpha_nose*Xcp_nose_in + ...
                 CNalpha_fins*Xcp_fins_in) / CNalpha_total;

stability_margin_in  = Xcp_total_in - CG_from_tip_in;
stability_margin_cal = stability_margin_in / D_body_in;

%% -------------------- FLUTTER (Martin / Apogee) ------------------------
% Aluminum fin can (≈6061-T6)
G_psi = 3.8e6;            % [psi] shear modulus

V_flutter = a_sos * sqrt( ...
    (G_psi * 2*(AR + 2) * (t_over_c^3)) / ...
    (1.337 * AR^3 * P_psi * (lambda + 1)) );

M_flutter = V_flutter / a_sos;
SF_flutter = V_flutter / V_max;

%% -------------------- SUMMARY OUTPUT -----------------------------------
fprintf('================ FAST 10k COTS – Fin & Stability Summary =============\n\n');

fprintf('--- From OpenRocket CSV ---\n');
fprintf('Max velocity V_max      : %.1f ft/s\n', V_max);
fprintf('Altitude at V_max       : %.1f ft\n\n', h_max);

fprintf('--- Rocket Geometry ---\n');
fprintf('Body diameter D         : %.3f in\n', D_body_in);
fprintf('Rocket length L         : %.2f in\n', L_rocket_in);
fprintf('Nose length (exposed)   : %.2f in\n\n', L_nose_in);

fprintf('--- Fin Geometry (actual polygon -> equivalent trapezoid) ---\n');
fprintf('Number of fins          : %d\n', n_fins);
fprintf('Semi-span (height)      : %.2f in\n', span_in);
fprintf('Single-fin area S       : %.2f in^2\n', S_fin_in2);
fprintf('Eq. root chord cr       : %.2f in\n', cr_in);
fprintf('Eq. tip chord  ct       : %.2f in\n', ct_in);
fprintf('Thickness t             : %.3f in\n', t_in);
fprintf('Aspect ratio AR         : %.3f [-]\n', AR);
fprintf('Taper ratio lambda      : %.3f [-]\n', lambda);
fprintf('Thickness ratio t/c     : %.4f [-]\n\n', t_over_c);

fprintf('--- Stability (OpenRocket) ---\n');
fprintf('CG from tip (OR)        : %.3f in\n', CG_from_tip_in_OR);
fprintf('CP from tip (OR)        : %.3f in\n', CP_from_tip_in_OR);
fprintf('Static margin (OR)      : %.2f calibers\n\n', SM_calibers_OR);

fprintf('--- Barrowman CP (optional cross-check) ---\n');
fprintf('CP (Barrowman)          : %.3f in from tip\n', Xcp_total_in);
fprintf('Static margin (Barrowman): %.2f in = %.2f calibers\n\n', ...
        stability_margin_in, stability_margin_cal);

fprintf('--- Flight Condition at V_max ---\n');
fprintf('Temperature T(h_max)    : %.1f R\n', T_R);
fprintf('Pressure P(h_max)       : %.3f psi\n', P_psi);
fprintf('Speed of sound a        : %.1f ft/s\n', a_sos);
fprintf('Mach at V_max           : %.3f\n\n', M_max);

fprintf('--- Fin Flutter (Martin / Apogee) ---\n');
fprintf('Shear modulus G         : %.2e psi\n', G_psi);
fprintf('Flutter speed V_f       : %.1f ft/s (Mach %.2f)\n', ...
        V_flutter, M_flutter);
fprintf('Flutter safety factor   : V_f / V_max = %.2f\n\n', SF_flutter);

fprintf('======================================================================\n');
if SF_flutter >= 1.5
    fprintf('Status: OK – Flutter speed is at least 1.5x higher than V_max.\n');
elseif SF_flutter >= 1.2
    fprintf('Status: Borderline – consider thicker fins, smaller span, or stiffer material.\n');
else
    fprintf('Status: NOT ACCEPTABLE – flutter too close to or below V_max.\n');
end
fprintf('======================================================================\n');
