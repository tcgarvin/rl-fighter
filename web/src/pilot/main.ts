// "How the pilot works": a static page (web/pilot/index.html). Its numbers are checked
// at build time by tools/pilot_facts.py, so the script only adds the site shell.
import { mountNav } from "../shell/nav";
import "./pilot.css";

mountNav("pilot");
