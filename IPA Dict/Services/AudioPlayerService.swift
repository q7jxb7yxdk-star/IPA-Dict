import AVFoundation
import Foundation

@MainActor
final class AudioPlayerService {
    static let shared = AudioPlayerService()

    static let phonemeAudioMap: [String: String] = [
        "æ": "ae",
        "ə": "schwa",
        "ɪ": "i_short",
        "iː": "i_long",
        "θ": "theta",
        "ð": "eth",
        "ʃ": "sh",
        "ʒ": "zh",
        "p": "p",
        "l": "l"
    ]

    private var audioPlayer: AVAudioPlayer?
    private var remotePlayer: AVPlayer?
    private let speechSynthesizer = AVSpeechSynthesizer()

    private init() {}

    func playSound(fileName: String) {
        let file = fileName as NSString
        let resourceName = file.deletingPathExtension
        let fileExtension = file.pathExtension.isEmpty ? "mp3" : file.pathExtension

        guard let url = Bundle.main.url(
            forResource: resourceName,
            withExtension: fileExtension
        ) else {
            print("Audio file not found in app bundle: \(resourceName).\(fileExtension)")
            return
        }

        do {
            #if os(iOS)
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .spokenAudio)
            try session.setActive(true)
            #endif

            audioPlayer = try AVAudioPlayer(contentsOf: url)
            audioPlayer?.prepareToPlay()
            audioPlayer?.play()
        } catch {
            print("Unable to play \(fileName): \(error.localizedDescription)")
        }
    }

    func playPhoneme(symbol: String) {
        guard let fileName = Self.phonemeAudioMap[symbol] else {
            print("No local audio mapping for phoneme: \(symbol)")
            return
        }

        playSound(fileName: fileName)
    }

    func playRemoteSound(url: URL) {
        remotePlayer = AVPlayer(url: url)
        remotePlayer?.play()
    }

    func speak(word: String, region: String) {
        let utterance = AVSpeechUtterance(string: word)
        utterance.voice = AVSpeechSynthesisVoice(
            language: region == "UK" ? "en-GB" : "en-US"
        )
        utterance.rate = 0.42
        speechSynthesizer.stopSpeaking(at: .immediate)
        speechSynthesizer.speak(utterance)
    }
}
