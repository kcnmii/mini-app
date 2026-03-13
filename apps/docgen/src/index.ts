import Docxtemplater from "docxtemplater";
import express from "express";
import ImageModule from "docxtemplater-image-module-free";
import lodash from "lodash";
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import PizZip from "pizzip";
import { z } from "zod";

const { get } = lodash;

const app = express();
const port = Number(process.env.PORT ?? 4001);
const templatesRoot = process.env.TEMPLATES_ROOT
  ? path.resolve(process.env.TEMPLATES_ROOT)
  : path.resolve(process.cwd(), "../../templates/system");

app.use(express.json({ limit: "10mb" }));

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "docgen" });
});

app.get("/templates", (_req, res) => {
  const templates = readdirSync(templatesRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .flatMap((entry) => {
      const templateDir = path.join(templatesRoot, entry.name);
      return readdirSync(templateDir, { withFileTypes: true })
        .filter((versionEntry) => versionEntry.isDirectory())
        .map((versionEntry) => {
          const manifestPath = path.join(
            templateDir,
            versionEntry.name,
            "manifest.json",
          );
          return JSON.parse(readFileSync(manifestPath, "utf-8"));
        });
    });

  res.json({ templates });
});

const renderRequestSchema = z.object({
  templateKey: z.string(),
  templateVersion: z.string(),
  data: z.record(z.unknown()),
});

function getTemplateDir(templateKey: string, templateVersion: string): string {
  return path.join(templatesRoot, templateKey, templateVersion);
}

// Transparent 1x1 PNG used as a placeholder when an image field is empty.
// This way the image module always receives valid data and the {%TAG}
// placeholder never leaks into the final document.
const TRANSPARENT_1PX_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB" +
  "Nl7BcQAAAABJRU5ErkJggg==",
  "base64",
);

function createImageModule() {
  return new ImageModule({
    centered: false,
    getImage(tagValue: string) {
      if (!tagValue || tagValue.length < 20) {
        return TRANSPARENT_1PX_PNG;
      }
      try {
        return Buffer.from(tagValue, "base64");
      } catch {
        return TRANSPARENT_1PX_PNG;
      }
    },
    getSize(_img: Buffer, tagValue: string, tagName: string) {
      // If no real image data — render at 1x1 so it's invisible
      if (!tagValue || tagValue.length < 20) {
        return [1, 1];
      }
      switch (tagName) {
        case "LOGO":
          return [100, 100];
        case "SIG":
          return [120, 50];
        case "STAMP":
          return [100, 100];
        default:
          return [100, 100];
      }
    },
  });
}

function createParser(tag: string) {
  const normalizedTag = tag.trim();
  return {
    get(scope: unknown) {
      return get(scope as object, normalizedTag, "");
    },
  };
}

app.post("/render/docx", (req, res) => {
  const parsed = renderRequestSchema.safeParse(req.body);

  if (!parsed.success) {
    return res.status(400).json({ error: "invalid_payload" });
  }

  const { templateKey, templateVersion, data } = parsed.data;
  const templateDir = getTemplateDir(templateKey, templateVersion);
  const templatePath = path.join(templateDir, "template.docx");

  try {
    const templateBuffer = readFileSync(templatePath);
    const zip = new PizZip(templateBuffer);
    const imageModule = createImageModule();

    const doc = new Docxtemplater(zip, {
      modules: [imageModule],
      linebreaks: true,
      paragraphLoop: true,
      parser: createParser,
      nullGetter() {
        return "";
      },
    });

    doc.render(data);
    const output = doc.getZip().generate({ type: "nodebuffer" });

    res.setHeader(
      "Content-Type",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    );
    res.setHeader(
      "Content-Disposition",
      `attachment; filename="${templateKey}-${templateVersion}.docx"`,
    );
    return res.send(output);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "unknown_error";
    console.error("render error:", error);
    return res.status(500).json({ error: "render_failed", detail });
  }
});

app.listen(port, () => {
  console.log(`docgen listening on ${port}`);
});
