// "How the commander works": a static page (web/commander/index.html). Its numbers are
// checked at build time by tools/commander_facts.py, so the script only adds the site
// shell. It shares the pilot page's layout and diagram styles.
import { mountNav } from "../shell/nav";
import "../pilot/pilot.css";
import "./commander.css";

mountNav("commander");
