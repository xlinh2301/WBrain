import 'package:nylo_framework/nylo_framework.dart';
import 'controller.dart';

class HomeController extends Controller {
  Future<void> onTapDocumentation() async {
    await openUrl("https://nylo.dev/docs");
  }

  Future<void> onTapGithub() async {
    await openUrl("https://github.com/nylo-core/nylo");
  }

  Future<void> onTapChangeLog() async {
    await openUrl("https://github.com/nylo-core/nylo/releases");
  }

  Future<void> onTapYouTube() async {
    await openUrl("https://m.youtube.com/@nylo_dev");
  }

  Future<void> onTapX() async {
    await openUrl("https://x.com/nylo_dev");
  }
}
